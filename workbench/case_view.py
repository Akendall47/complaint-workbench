"""Everything the Case page shows, gathered into one dict. Reads only; every change goes through workbench.cases."""
import json
import re
from datetime import date

from . import cases, drafts
from .deadlines import business_days_left
from .handover import missing_fields
from .search import search_policies
from .urgency import urgent_reasons

WORKERS = cases.WORKERS
MONEY = {"amount_disputed", "monthly_income", "monthly_outgoings", "total_arrears", "amount_lost"}  # shown with a pound sign
ACTION = {"open_case": "Opened", "confirm_claim": "Claim confirmed", "edit_claim": "Claim edited", "remove_claim": "Claim removed",
          "add_claim": "Claim added", "reject_draft": "AI draft rejected", "set_handover": "Handover saved", "approve": "Approved and sent",
          "accept": "Accepted", "return_case": "Returned", "assign": "Assigned", "set_urgent": "Urgent flag changed",
          "set_department": "Department changed", "unmask": "Unmasked notes"}


def split_note(body: str, marks: list[tuple[int, str]]) -> list[tuple[str, int | None]]:
    """Cut a note into (text, claim number) parts. Each part is escaped by the template, so no HTML is built here."""
    found: list[tuple[int, int, int]] = []
    for no, quote in marks:
        words = quote.split()
        m = re.search(r"\s+".join(map(re.escape, words)), body, re.I) if words else None
        if m and all(m.end() <= s or m.start() >= e for s, e, _ in found):
            found.append((m.start(), m.end(), no))
    out, pos = [], 0
    for s, e, no in sorted(found):
        if s > pos:
            out.append((body[pos:s], None))
        out.append((body[s:e], no))
        pos = e
    if pos < len(body) or not out:
        out.append((body[pos:], None))
    return out


def _detail(raw: str) -> dict:
    try:
        d = json.loads(raw or "{}")
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def money_text(v: str) -> tuple[str, bool]:
    """A money value as shown: numbers get thousands separators and two decimals, anything else stays as typed."""
    n = (v or "").strip().removeprefix("£").replace(",", "")
    return (f"{float(n):,.2f}", True) if re.fullmatch(r"\d+(\.\d+)?", n) else (v, False)


def build(conn, cfg, case_id, actor, step=1, all_=False, unmasked=False) -> dict | None:
    c = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if c is None:
        return None
    today = date.fromisoformat(cfg["today"])
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    raw_notes = conn.execute("SELECT id, seq, author, written_at, body FROM notes WHERE case_id = ? ORDER BY seq", (case_id,)).fetchall()
    shown = {nid: body for _, nid, body in drafts.masked_notes(conn, case_id, cfg)}
    rows = conn.execute("SELECT * FROM claims WHERE case_id = ? AND status != 'removed' ORDER BY seq", (case_id,)).fetchall()
    claims = []
    for i, r in enumerate(rows, 1):
        claims.append({"no": i, "id": r["id"], "text": r["text"], "quote": r["quote"], "note_id": r["note_id"], "status": r["status"],
                       "inferred": bool(r["inferred"]), "supported": bool(r["supported"]), "by_hand": r["quote"] is None})
    notes = []
    for n in raw_notes:
        body = n["body"] if unmasked else shown[n["id"]]
        marks = [(x["no"], x["quote"]) for x in claims if x["note_id"] == n["id"] and x["supported"] and x["quote"]]  # unmasked too: a quote with no masked words still matches
        parts = split_note(body, marks)
        for _, no in parts:
            for x in claims:
                if x["no"] == no:
                    x["located"] = True
        notes.append({"seq": n["seq"], "author": n["author"], "at": (n["written_at"] or "")[:10], "parts": parts})
    worker = actor.role in WORKERS
    editable = worker and c["state"] == "in_review"
    dept = cfg["departments"].get(c["department"]) if c["department"] else None
    saved = json.loads(c["handover_json"] or "{}")
    suggested = drafts.load_handover(conn, case_id, cfg) if editable else {}
    fields, missing = [], []
    if dept:
        missing = missing_fields(c["department"], saved, cfg)
        fields = []
        for f in sorted(dept["required_fields"], key=lambda f: f not in missing):
            raw = saved.get(f) or suggested.get(f, "")
            text, num = money_text(raw) if f in MONEY else (raw, False)
            fields.append({"name": f, "label": f.replace("_", " ").capitalize(), "value": text, "money": f in MONEY and (num or not raw),
                           "missing": f in missing, "suggested": not saved.get(f) and f in suggested})
    ok, why = cases.can_approve(conn, case_id)
    reviewed = sum(x["status"] in ("confirmed", "edited") for x in claims)
    all_notes = " ".join(n["body"] for n in raw_notes)
    # The days left are already in the header, so deadline reasons are not repeated there.
    reasons = [r for r in urgent_reasons(c, all_notes, today, cfg) if "deadline" not in r.lower()] if c["urgent"] else []
    if c["urgent"] and c["urgent_manual"] is not None:
        reasons.append("Set by hand")
    ret = None
    if c["return_count"] and c["state"] in ("returned", "in_review"):
        r = conn.execute("SELECT detail_json FROM audit WHERE case_id = ? AND action = 'return_case' ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
        ret = _detail(r[0]).get("reason") if r else None
    trail = [{"at": r["at"][:16].replace("T", " "), "what": ACTION.get(r["action"], r["action"]), "reason": _detail(r["detail_json"]).get("reason"),
              "who": "System" if r["actor_id"] == "system" else f"{r['name'] or r['actor_id']}, {r['role'].replace('_', ' ').capitalize()}"}
             for r in conn.execute("SELECT a.at, a.actor_id, a.role, a.action, a.detail_json, s.name FROM audit a LEFT JOIN staff s ON s.id = a.actor_id"
                                   " WHERE a.case_id = ? ORDER BY a.id", (case_id,))]
    query = " ".join([c["type"] or ""] + [x["text"] for x in claims if x["status"] in ("confirmed", "edited")])
    policies = search_policies(conn, query, 5) if c["state"] != "accepted" or claims else []
    can_decide, decide_msg = cases.can_decide(conn, case_id, actor)
    all_ = all_ or not editable
    step = step if step in (1, 2, 3) else 1
    owner = conn.execute("SELECT name FROM staff WHERE id = ?", (c["owner_id"],)).fetchone()
    return {"c": c, "id": case_id, "owner_name": owner[0] if owner else None, "step": step, "all": all_, "unmasked": unmasked, "worker": worker, "editable": editable,
            "days": business_days_left(date.fromisoformat(c["deadline"]), today, hol), "reasons": reasons, "returned_reason": ret,
            "notes": notes, "claims": claims, "reviewed": reviewed, "fields": fields, "missing": len(missing), "has_dept": bool(dept),
            "can_approve": ok, "why": why, "next_action": cases.next_action(conn, case_id, actor.role), "trail": trail,
            "policies": policies, "departments": list(cfg["departments"]), "draft_state": c["draft_state"],
            "has_decision": (editable and c["state"] in ("new", "returned", "in_review")) or (worker and c["state"] in ("new", "returned")) or can_decide, "can_decide": can_decide, "decide_msg": decide_msg, "locked": editable and not ok, "first_pending": next((x["id"] for x in claims if x["status"] == "draft" and x["supported"]), None)}
