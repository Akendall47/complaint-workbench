import sqlite3
from datetime import date

from workbench import audit
from workbench.classify import looks_english, predict
from workbench.deadlines import deadline_for
from workbench.urgency import is_urgent

PAYMENT_TYPES = ("Payment scam", "Fraud or security")  # the types the generator treats as payment complaints


MAX_TEXT = 5000  # characters; the form limits its text box to this too


class IntakeError(ValueError):
    pass


def _norm(s: str) -> str:
    return " ".join(s.casefold().split())


def receive(conn: sqlite3.Connection, *, text: str, source: str, cfg: dict, models: dict, actor_id: str = "system", role: str = "system") -> str:
    if not text or not text.strip():
        raise IntakeError("Enter the complaint text.")
    if source not in cfg["sources"]:
        raise IntakeError("Choose where the complaint came from.")
    if len(text) > MAX_TEXT:
        raise IntakeError(f"Complaint text is too long. The limit is {MAX_TEXT:,} characters.")
    text = text.strip()
    key = _norm(text)
    dep, ty = predict(models["department"], text), predict(models["type"], text)
    routed = dep.label if dep.confidence >= cfg["routing_threshold"] and looks_english(text) else None
    kind = "payment" if ty.label in PAYMENT_TYPES else "other"
    today = date.fromisoformat(cfg["today"])
    now = f"{today.isoformat()}T12:30:00"  # the demo clock the generator uses for "now"
    case = {"state": "new", "deadline": str(deadline_for(today, kind, cfg)), "return_count": 0, "urgent_manual": None}
    try:
        if not conn.in_transaction:
            conn.execute("BEGIN IMMEDIATE")  # take the write lock before reading, so two intakes cannot share an id
        # shortcut: scans note 1 of every case per intake (about 1,600 rows, a few ms); store a hash column and index it past ~100k cases.
        dup = next((r["case_id"] for r in conn.execute("SELECT case_id, body FROM notes WHERE seq = 1 ORDER BY case_id")
                    if _norm(r["body"]) == key), None)
        # the write lock taken above makes MAX(id) + 1 safe: no second intake can read the same maximum
        last = conn.execute("SELECT MAX(id) FROM cases").fetchone()[0]
        cid = f"AB-2026-{(int(last.rsplit('-', 1)[1]) if last else 0) + 1:05d}"
        conn.execute(
            "INSERT INTO cases(id, received_at, source, product_kind, department, department_pred, department_conf, type, type_conf,"
            " state, urgent, return_count, deadline, duplicate_of, draft_state, customer_json, handover_json, version)"
            " VALUES (?,?,?,?,?,?,?,?,?,'new',?,0,?,?,'none','{}','{}',0)",
            (cid, now, source, kind, routed, dep.label, dep.confidence, ty.label, ty.confidence,
             int(is_urgent(case, text, today, cfg)), case["deadline"], dup))
        conn.execute("INSERT INTO notes(case_id, seq, author, written_at, body) VALUES (?,?,?,?,?)", (cid, 1, "customer", now, text))
        conn.execute("INSERT INTO events(case_id, at, kind, from_state, to_state, actor_id) VALUES (?,?,?,?,?,?)",
                     (cid, now, "received", None, "new", actor_id))
        audit.append(conn, actor_id=actor_id, role=role, action="received", case_id=cid,
                     detail={"source": source, "duplicate_of": dup, "department": routed})
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return cid
