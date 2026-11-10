"""Reads a recorded model answer and stores its claims. Trusts nothing in the file."""
import json
import re
from pathlib import Path

from .citations import quote_in_source
from .masking import mask

MAX_CLAIMS = 8
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
TAG = re.compile(r"<[^>]*>")


def clean(s: str) -> str:
    return " ".join(TAG.sub("", LINK.sub(r"\1", IMAGE.sub("", s))).split())


def rec_path(cfg: dict, case_id: str, dev: bool = False) -> Path:
    base = cfg.get("recordings_dir") or ("data/recordings-dev" if dev else "data/recordings")
    return Path(base) / f"{case_id}.json"


def parse(raw_output: str) -> dict | None:
    """The draft only if it has the Draft shape with 1 to 8 claims. Strings lose links, images and tags."""
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
    except (ValueError, KeyError, TypeError):
        return None


def known_values(conn, case_id: str) -> dict:
    c = json.loads(conn.execute("SELECT customer_json FROM cases WHERE id = ?", (case_id,)).fetchone()[0])
    return {"name": c.get("name"), "address": c.get("address"), "dob": c.get("date_of_birth")}


def masked_notes(conn, case_id: str, cfg: dict) -> list[tuple[int, int, str]]:
    """(seq, note id, masked body) for each note, in order."""
    known = known_values(conn, case_id)
    rows = conn.execute("SELECT id, seq, body FROM notes WHERE case_id = ? ORDER BY seq", (case_id,)).fetchall()
    return [(r["seq"], r["id"], mask(r["body"], known, cfg["masking"])) for r in rows]


def store_claims(conn, case_id: str, cfg: dict) -> str:
    """Parse the recording, check every quote against the masked note, store draft claims. Never touches state, owner or urgency."""
    path = rec_path(cfg, case_id)
    if not path.exists():
        return "none"
    cur = conn.execute("SELECT draft_state FROM cases WHERE id = ?", (case_id,)).fetchone()[0]
    if cur == "rejected" or conn.execute(
            "SELECT 1 FROM claims WHERE case_id = ? AND status != 'draft'", (case_id,)).fetchone():
        return cur  # a person has already acted on this draft
    try:
        raw = json.loads(path.read_text(encoding="utf-8")).get("raw_output")
        draft = parse(raw) if isinstance(raw, str) else None
    except (ValueError, AttributeError):
        draft = None
    conn.execute("DELETE FROM claims WHERE case_id = ?", (case_id,))
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
