"""Reads a recorded model answer and stores its claims. Trusts nothing in the file."""
import json
import re
from pathlib import Path

from .citations import quote_in_source
from .masking import mask

MAX_CLAIMS = 8
IMAGE = re.compile(r"!\[[^\[\]]*\]\([^)]*\)")  # no "[" inside: keeps a run of unclosed brackets linear
LINK = re.compile(r"\[([^\[\]]*)\]\([^)]*\)")
TAG = re.compile(r"<[^<>]*>")


ROOT = Path(__file__).resolve().parent.parent
CASE_ID = re.compile(r"AB-\d{4}-\d{5}", re.ASCII)
MAX_RAW = 20_000


def clean(s: str) -> str:
    """Remove links, images and tags until nothing changes, then any leftover markup characters."""
    while True:
        t = TAG.sub("", LINK.sub(r"\1", IMAGE.sub("", s)))
        for bad in ("<", ">", "](", "!["):
            t = t.replace(bad, "")
        if t == s:
            break
        s = t
    return " ".join(s.split())


def rec_path(cfg: dict, case_id: str, dev: bool = False) -> Path:
    base = cfg.get("recordings_dir") or ("data/recordings-dev" if dev else "data/recordings")
    return ROOT / base / f"{case_id}.json"


def parse(raw_output: str) -> dict | None:
    """The draft only if it has the Draft shape with 1 to 8 claims. Strings lose links, images and tags."""
    if len(raw_output) > MAX_RAW:
        return None
    try:
        d = json.loads(raw_output)
        claims, handover = d["claims"], d["handover"]
        if not (isinstance(claims, list) and 1 <= len(claims) <= MAX_CLAIMS and isinstance(handover, dict)):
            return None
        out = []
        for c in claims:
            if not (isinstance(c["text"], str) and isinstance(c["quote"], str)
                    and type(c["note"]) is int and type(c["inferred"]) is bool):
                return None
            out.append({"text": clean(c["text"]), "quote": clean(c["quote"]),
                        "note": c["note"], "inferred": c["inferred"]})
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in handover.items()):
            return None
        return {"claims": out, "handover": {clean(k): clean(v) for k, v in handover.items()}}
    except (ValueError, KeyError, TypeError, RecursionError):
        return None


def known_values(conn, case_id: str) -> dict:
    c = json.loads(conn.execute("SELECT customer_json FROM cases WHERE id = ?", (case_id,)).fetchone()[0])
    return {"name": c.get("name"), "address": c.get("address"), "dob": c.get("date_of_birth")}


def masked_notes(conn, case_id: str, cfg: dict) -> list[tuple[int, int, str]]:
    """(seq, note id, masked body) for each note, in order."""
    known = known_values(conn, case_id)
    rows = conn.execute("SELECT id, seq, body FROM notes WHERE case_id = ? ORDER BY seq", (case_id,)).fetchall()
    return [(r["seq"], r["id"], mask(r["body"], known, cfg["masking"])) for r in rows]


def _raw_output(case_id: str, cfg: dict) -> str | None:
    """The recording's raw_output, or None if there is no valid case id or no file. Unreadable gives an empty string."""
    if not CASE_ID.fullmatch(case_id):
        return None
    path = rec_path(cfg, case_id)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8")).get("raw_output")
    except (ValueError, AttributeError, RecursionError):
        return ""
    return raw if isinstance(raw, str) else ""


def load_handover(conn, case_id: str, cfg: dict) -> dict:
    """Suggested handover values from the recording, for the department's fields only. Never written to the case."""
    raw = _raw_output(case_id, cfg)
    row = conn.execute("SELECT department FROM cases WHERE id = ?", (case_id,)).fetchone()
    draft = parse(raw) if raw else None
    if draft is None or row is None or row[0] not in cfg["departments"]:
        return {}
    fields = cfg["departments"][row[0]]["required_fields"]
    return {k: v for k, v in draft["handover"].items() if k in fields}


def store_claims(conn, case_id: str, cfg: dict) -> str:
    """Parse the recording, check every quote against the masked note, store draft claims.

    Never touches state, owner or urgency. If the case already has claim rows it changes nothing."""
    raw = _raw_output(case_id, cfg)
    row = conn.execute("SELECT draft_state FROM cases WHERE id = ?", (case_id,)).fetchone()
    if raw is None or row is None:
        return "none"
    if row[0] == "rejected" or conn.execute("SELECT 1 FROM claims WHERE case_id = ?", (case_id,)).fetchone():
        return row[0]
    draft = parse(raw)
    if draft is None:
        state = "invalid"
    else:
        notes = {seq: (nid, text) for seq, nid, text in masked_notes(conn, case_id, cfg)}
        for i, c in enumerate(draft["claims"], 1):
            nid, text = notes.get(c["note"], (None, ""))
            ok = int(nid is not None and quote_in_source(c["quote"], text))
            conn.execute(
                "INSERT INTO claims(case_id, seq, text, quote, note_id, inferred, supported, status) "
                "VALUES (?,?,?,?,?,?,?,'draft')",
                (case_id, i, c["text"], c["quote"], nid, int(c["inferred"]), ok))
        state = "available"
    conn.execute("UPDATE cases SET draft_state = ? WHERE id = ?", (state, case_id))
    conn.commit()
    return state
