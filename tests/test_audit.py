import sqlite3

import pytest

from workbench import audit


@pytest.fixture
def three(conn):
    for i in range(3):
        audit.append(conn, actor_id="H1", role="handler", action=f"a{i}", case_id="AB-2026-00001", detail={"i": i})


def test_audit_chain_verifies_after_three_appends(conn, three):
    assert audit.verify_chain(conn) is None


def test_update_refused(conn, three):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE audit SET action='x'")


def test_delete_refused(conn, three):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM audit")


def test_tamper_detected(conn, three):
    conn.execute("DROP TRIGGER audit_no_update")
    conn.execute("UPDATE audit SET action='x' WHERE id=2")
    assert audit.verify_chain(conn) == 2


def test_delete_newest_detected(conn, three):
    conn.execute("DROP TRIGGER audit_no_delete")
    conn.execute("DELETE FROM audit WHERE id=3")
    assert audit.verify_chain(conn) == 3


def test_delete_middle_detected(conn, three):
    conn.execute("DROP TRIGGER audit_no_delete")
    conn.execute("DELETE FROM audit WHERE id=2")
    assert audit.verify_chain(conn) == 2


def test_empty_log_ok(conn):
    assert audit.verify_chain(conn) is None


def test_detail_change_detected(conn, three):
    conn.execute("DROP TRIGGER audit_no_update")
    conn.execute("UPDATE audit SET detail_json='{}' WHERE id=3")
    assert audit.verify_chain(conn) == 3


def test_append_does_not_commit(conn):
    audit.append(conn, actor_id="H1", role="handler", action="a")
    assert conn.in_transaction
    conn.rollback()
    assert conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 0
