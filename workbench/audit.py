import hashlib
import json
import sqlite3
from datetime import datetime, timezone

ZEROS = "0" * 64


def _hash(prev, at, actor_id, role, case_id, action, detail_json):
    return hashlib.sha256((prev + at + actor_id + role + (case_id or "") + action + detail_json).encode()).hexdigest()


def append(conn: sqlite3.Connection, *, actor_id: str, role: str, action: str,
           case_id: str | None = None, detail: dict | None = None) -> int:
    row = conn.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
    prev = row["hash"] if row else ZEROS
    at = datetime.now(timezone.utc).isoformat()
    detail_json = json.dumps(detail, sort_keys=True)
    h = _hash(prev, at, actor_id, role, case_id, action, detail_json)
    cur = conn.execute(
        "INSERT INTO audit(at, actor_id, role, case_id, action, detail_json, prev_hash, hash)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (at, actor_id, role, case_id, action, detail_json, prev, h))
    conn.commit()
    return cur.lastrowid


def verify_chain(conn: sqlite3.Connection) -> int | None:
    prev = ZEROS
    for r in conn.execute("SELECT * FROM audit ORDER BY id"):
        if r["prev_hash"] != prev or r["hash"] != _hash(
                prev, r["at"], r["actor_id"], r["role"], r["case_id"], r["action"], r["detail_json"]):
            return r["id"]
        prev = r["hash"]
    return None
