"""Every change a person can make to a case. Each function is one transaction: the case change, the event
and the audit row commit together or not at all. Nothing else (a draft, a recording, note text) changes a case."""
import json
from datetime import date
from typing import NamedTuple

from . import audit
from .config import load_config
from .handover import missing_fields
from .urgency import is_urgent

WORKERS = {"handler", "team_lead"}
KIND = {"in_review": "opened", "handed_over": "handed_over", "returned": "returned", "accepted": "accepted"}


class Actor(NamedTuple):
    id: str
    role: str


class StaleCase(Exception):
    pass


class NotAllowed(Exception):
    pass


AT = object()  # in a changes dict: replaced by the action's one timestamp


def _do(conn, case_id, actor, version, action, roles, fn, bump=True):
    """The shared steps: lock, actor check, role check, version check, run fn, write, event, audit, commit.
    fn(case) returns (detail, changes) where changes is a dict of cases columns to set.
    The connection must be outside a transaction on entry: the action owns the whole transaction."""
    if conn.in_transaction:
        raise RuntimeError("cases actions must start outside a transaction")
    try:
        conn.execute("BEGIN IMMEDIATE")  # take the write lock before reading
        if not conn.execute("SELECT 1 FROM staff WHERE id = ? AND role = ?", (actor.id, actor.role)).fetchone():
            raise NotAllowed("Your sign-in is not recognised.")
        case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if case is None:
            raise NotAllowed("That case does not exist.")
        if actor.role not in roles:
            raise NotAllowed("Your role cannot do this.")
        if case["version"] != version:
            raise StaleCase("This case changed since you opened it. Reload to see the latest.")
        detail, changes = fn(case)
        at = audit.now()  # the one timestamp for the case columns, the event and the audit row
        changes = {k: at if v is AT else v for k, v in changes.items()}
        if bump:
            sets = {**changes, "version": version + 1}
            cur = conn.execute(
                f"UPDATE cases SET {', '.join(k + ' = ?' for k in sets)} WHERE id = ? AND version = ?",
                (*sets.values(), case_id, version))
            if cur.rowcount != 1:
                raise StaleCase("This case changed since you opened it. Reload to see the latest.")
        new = changes.get("state")
        if new:
            conn.execute("INSERT INTO events(case_id, at, kind, from_state, to_state, actor_id) VALUES (?,?,?,?,?,?)",
                         (case_id, at, KIND[new], case["state"], new, actor.id))
            fresh = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
            if fresh["urgent_manual"] is None:
                notes = " ".join(r[0] for r in conn.execute("SELECT body FROM notes WHERE case_id = ?", (case_id,)))
                cfg = load_config()
                u = int(is_urgent(fresh, notes, date.fromisoformat(cfg["today"]), cfg))
                conn.execute("UPDATE cases SET urgent = ? WHERE id = ?", (u, case_id))
        audit.append(conn, actor_id=actor.id, role=actor.role, action=action, case_id=case_id, detail=detail, at=at)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def _text(s, lo, hi, what):
    s = (s or "").strip()
    if not lo <= len(s) <= hi:
        raise NotAllowed(f"{what} must be {lo} to {hi} characters." if lo > 1 else
                         f"{what} must be 1 to {hi} characters.")
    return s


def _reason(s):
    s = (s or "").strip()
    if len(s) < 10:
        raise NotAllowed("Give a reason of at least 10 characters.")
    if len(s) > 500:
        raise NotAllowed("The reason must be 500 characters or fewer.")
    return s


def _need_state(case, *states):
    if case["state"] not in states:
        names = " or ".join(s.replace("_", " ") for s in states)
        raise NotAllowed(f"This only works on a case that is {names}.")


def _claim(conn, case, claim_id):
    c = conn.execute("SELECT * FROM claims WHERE id = ? AND case_id = ?", (claim_id, case["id"])).fetchone()
    if c is None or c["status"] == "removed":
        raise NotAllowed("That claim is not on this case.")
    return c


def _specialist(conn, case, actor):
    dept = conn.execute("SELECT department FROM staff WHERE id = ? AND role = 'specialist'", (actor.id,)).fetchone()
    if dept is None or dept[0] != case["department"]:
        raise NotAllowed(f"Only the {case['department']} specialist can do this.")


def open_case(conn, case_id, actor, version):
    def fn(c):
        _need_state(c, "new", "returned")
        return {"from": c["state"]}, {"state": "in_review", "owner_id": c["owner_id"] or actor.id}
    _do(conn, case_id, actor, version, "open_case", WORKERS, fn)


def confirm_claim(conn, case_id, actor, version, claim_id):
    def fn(c):
        _need_state(c, "in_review")
        cl = _claim(conn, c, claim_id)
        if cl["status"] != "draft":
            raise NotAllowed("Only a draft claim can be confirmed.")
        if not cl["supported"]:
            raise NotAllowed("This claim has no matching quote in the notes. Edit it or remove it.")
        conn.execute("UPDATE claims SET status = 'confirmed' WHERE id = ?", (claim_id,))
        return {"claim_id": claim_id}, {}
    _do(conn, case_id, actor, version, "confirm_claim", WORKERS, fn)


def edit_claim(conn, case_id, actor, version, claim_id, text):
    def fn(c):
        _need_state(c, "in_review")
        cl = _claim(conn, c, claim_id)
        t = _text(text, 1, 600, "The claim")
        conn.execute("UPDATE claims SET text = ?, status = 'edited', original_text = COALESCE(original_text, ?) WHERE id = ?",
                     (t, cl["text"] if cl["quote"] else None, claim_id))
        return {"claim_id": claim_id, "was_length": len(cl["text"]), "now_length": len(t)}, {}
    _do(conn, case_id, actor, version, "edit_claim", WORKERS, fn)


def remove_claim(conn, case_id, actor, version, claim_id):
    def fn(c):
        _need_state(c, "in_review")
        _claim(conn, c, claim_id)
        conn.execute("UPDATE claims SET status = 'removed' WHERE id = ?", (claim_id,))
        return {"claim_id": claim_id}, {}
    _do(conn, case_id, actor, version, "remove_claim", WORKERS, fn)


def add_claim(conn, case_id, actor, version, text):
    def fn(c):
        _need_state(c, "in_review")
        t = _text(text, 1, 600, "The claim")
        seq = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM claims WHERE case_id = ?", (case_id,)).fetchone()[0]
        conn.execute("INSERT INTO claims(case_id, seq, text, inferred, supported, status) VALUES (?,?,?,0,0,'edited')",
                     (case_id, seq, t))
        return {"length": len(t)}, {}
    _do(conn, case_id, actor, version, "add_claim", WORKERS, fn)


def reject_draft(conn, case_id, actor, version, reason):
    def fn(c):
        _need_state(c, "in_review")
        r = _reason(reason)
        if c["draft_state"] not in ("available", "invalid"):
            raise NotAllowed("There is no AI draft to reject.")
        conn.execute("UPDATE claims SET status = 'removed' WHERE case_id = ? AND status = 'draft'", (case_id,))
        return {"reason": r}, {"draft_state": "rejected"}
    _do(conn, case_id, actor, version, "reject_draft", WORKERS, fn)


def set_handover(conn, case_id, actor, version, fields):
    def fn(c):
        _need_state(c, "in_review")
        if not c["department"]:
            raise NotAllowed("Set the department first.")
        if not isinstance(fields, dict) or not all(isinstance(v, str) for v in fields.values()):
            raise NotAllowed("The handover fields must be text.")
        dept = load_config()["departments"].get(c["department"])
        if dept is None:
            raise NotAllowed("Set the department first.")
        allowed = dept["required_fields"]
        bad = [f for f in fields if f not in allowed]
        if bad:
            raise NotAllowed(f"{bad[0]} is not part of the {c['department']} handover.")
        new = {f: _text(v, 0, 300, "A handover field") if v.strip() else "" for f, v in fields.items()}
        pack = {**json.loads(c["handover_json"] or "{}"), **new}
        return {"fields": sorted(new)}, {"handover_json": json.dumps(pack)}
    _do(conn, case_id, actor, version, "set_handover", WORKERS, fn)


def can_approve(conn, case_id) -> tuple[bool, str]:
    c = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if c["state"] != "in_review":
        return False, "Only a case in review can be sent"
    if not c["department"]:
        return False, "Set the department first"
    st = [r[0] for r in conn.execute("SELECT status FROM claims WHERE case_id = ?", (case_id,))]
    if (n := st.count("draft")):
        return False, f"Confirm, edit or remove {n} more claim{'s' * (n != 1)}"
    if all(s == "removed" for s in st):
        return False, "Add at least one claim"
    m = missing_fields(c["department"], json.loads(c["handover_json"] or "{}"), load_config())
    return True, f"Ready to send, pack incomplete ({len(m)} missing)" if m else "Ready to send"


def approve(conn, case_id, actor, version):
    def fn(c):
        ok, msg = can_approve(conn, case_id)
        if not ok:
            raise NotAllowed(msg)
        missing = missing_fields(c["department"], json.loads(c["handover_json"] or "{}"), load_config())
        spec = conn.execute("SELECT id FROM staff WHERE role = 'specialist' AND department = ?", (c["department"],)).fetchone()
        # Same as the generator: T1 keeps a case returned twice; else the specialist if the department has one; else the handler.
        owner = c["owner_id"] if (c["return_count"] or 0) >= 2 else (spec[0] if spec else c["owner_id"])
        return ({"missing": missing, "incomplete": bool(missing), "department": c["department"]},
                {"state": "handed_over", "owner_id": owner, "handed_over_at": AT})
    _do(conn, case_id, actor, version, "approve", WORKERS, fn)


def accept(conn, case_id, actor, version):
    def fn(c):
        _need_state(c, "handed_over")
        _specialist(conn, c, actor)
        return {}, {"state": "accepted", "accepted_at": AT}
    _do(conn, case_id, actor, version, "accept", {"specialist"}, fn)


def return_case(conn, case_id, actor, version, reason):
    def fn(c):
        _need_state(c, "handed_over")
        _specialist(conn, c, actor)
        r = _reason(reason)
        rc = (c["return_count"] or 0) + 1
        h = conn.execute("SELECT actor_id FROM events WHERE case_id = ? AND kind = 'handed_over' ORDER BY id DESC LIMIT 1",
                         (case_id,)).fetchone()
        owner = "T1" if rc >= 2 else (h[0] if h else c["owner_id"])
        return {"reason": r, "return_count": rc}, {"state": "returned", "return_count": rc, "owner_id": owner}
    _do(conn, case_id, actor, version, "return_case", {"specialist"}, fn)


def assign(conn, case_id, actor, version, owner_id):
    def fn(c):
        _need_state(c, "new", "in_review", "handed_over", "returned")
        if not conn.execute("SELECT 1 FROM staff WHERE id = ?", (owner_id,)).fetchone():
            raise NotAllowed("No such member of staff.")
        if c["owner_id"] == owner_id:
            raise NotAllowed(f"Already assigned to {owner_id}.")
        if actor.role == "handler":
            if c["owner_id"]:
                raise NotAllowed("This case already has an owner. Ask a team lead to reassign it.")
            if owner_id != actor.id:
                raise NotAllowed("You can only assign a case to yourself.")
        return {"from": c["owner_id"], "to": owner_id}, {"owner_id": owner_id}
    _do(conn, case_id, actor, version, "assign", WORKERS, fn)


def set_urgent(conn, case_id, actor, version, urgent, reason):
    def fn(c):
        _need_state(c, "new", "in_review", "handed_over", "returned")
        r = _reason(reason)
        return {"urgent": bool(urgent), "reason": r}, {"urgent": int(bool(urgent)), "urgent_manual": int(bool(urgent))}
    _do(conn, case_id, actor, version, "set_urgent", WORKERS, fn)


def set_department(conn, case_id, actor, version, department):
    def fn(c):
        _need_state(c, "new", "in_review", "returned")
        if department not in load_config()["departments"]:
            raise NotAllowed("Choose a department from the list.")
        return {"from": c["department"], "to": department}, {"department": department}
    _do(conn, case_id, actor, version, "set_department", WORKERS, fn)


def unmask(conn, case_id, actor, version, reason) -> None:
    """Logged only. The route then shows the unmasked notes once. The case does not change, so the version stays.
    A specialist may unmask only a handed-over or accepted case of their own department."""
    def fn(c):
        if actor.role == "specialist":
            _need_state(c, "handed_over", "accepted")
            _specialist(conn, c, actor)
        return {"reason": _reason(reason)}, {}
    _do(conn, case_id, actor, version, "unmask", WORKERS | {"specialist"}, fn, bump=False)


def next_action(conn, case_id, role) -> str:
    c = conn.execute("SELECT state, department FROM cases WHERE id = ?", (case_id,)).fetchone()
    s, d = c["state"], c["department"]
    if role == "specialist":
        return "Accept, or return with a reason" if s == "handed_over" else "Nothing for you to do yet"
    return {"new": "Open the case to start the review", "in_review": can_approve(conn, case_id)[1],
            "handed_over": f"Waiting for {d} to accept", "returned": "Returned. Read the reason, then reopen",
            "accepted": f"Accepted by {d}. Nothing more to do"}[s]
