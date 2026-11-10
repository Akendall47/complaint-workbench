import json
from datetime import datetime

import pytest

from workbench import audit, cases
from workbench.cases import Actor, NotAllowed, StaleCase
from workbench.generate import STAFF

H1, H2, S1, S2, T1 = (Actor("H1", "handler"), Actor("H2", "handler"), Actor("S1", "specialist"),
                      Actor("S2", "specialist"), Actor("T1", "team_lead"))
FRAUD = {"amount_disputed": "12.50", "date_of_transaction": "1 Nov", "merchant_name": "X", "card_last_four": "1234",
         "police_reference": "P1"}


@pytest.fixture(autouse=True)
def demo_clock():
    audit.set_clock(lambda: datetime(2026, 11, 10, 12, 30))
    yield
    audit.set_clock(None)


@pytest.fixture
def k(conn):
    conn.executemany("INSERT INTO staff VALUES (?,?,?,?)", STAFF)
    conn.execute("INSERT INTO cases(id, received_at, deadline, state, owner_id, urgent, department, return_count, handover_json, draft_state, version)"
                 " VALUES ('C1','2026-11-09T09:00:00','2027-01-01','new','H1',0,'Fraud claims',0,'{}','available',0)")
    for i, sup in enumerate([1, 1, 0], 1):
        conn.execute("INSERT INTO claims(case_id, seq, text, quote, inferred, supported, status) VALUES ('C1',?,?,?,0,?,'draft')",
                     (i, f"claim {i}", "q", sup))
    conn.commit()
    return conn


def row(c, cid="C1"):
    return c.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()


def ver(c):
    return row(c)["version"]


def claim_ids(c):
    return [r[0] for r in c.execute("SELECT id FROM claims WHERE case_id='C1' ORDER BY seq")]


def audits(c):
    return c.execute("SELECT COUNT(*) FROM audit").fetchone()[0]


def ready(c):
    """Case in review, all claims dealt with, pack complete."""
    cases.open_case(c, "C1", H1, ver(c))
    a, b, d = claim_ids(c)
    cases.confirm_claim(c, "C1", H1, ver(c), a)
    cases.confirm_claim(c, "C1", H1, ver(c), b)
    cases.remove_claim(c, "C1", H1, ver(c), d)
    cases.set_handover(c, "C1", H1, ver(c), FRAUD)


def test_open_moves_to_in_review_and_logs_event(k):
    cases.open_case(k, "C1", H1, 0)
    r = row(k)
    assert (r["state"], r["version"]) == ("in_review", 1)
    ev = k.execute("SELECT * FROM events WHERE case_id='C1'").fetchone()
    assert (ev["kind"], ev["from_state"], ev["to_state"], ev["actor_id"], ev["at"]) == (
        "opened", "new", "in_review", "H1", "2026-11-10T12:30:00")


def test_open_sets_owner_when_none(k):
    k.execute("UPDATE cases SET owner_id=NULL")
    k.commit()
    cases.open_case(k, "C1", H2, 0)
    assert row(k)["owner_id"] == "H2"


def test_approve_refused_while_any_claim_is_draft(k):
    cases.open_case(k, "C1", H1, 0)
    ok, msg = cases.can_approve(k, "C1")
    assert not ok and msg == "Confirm, edit or remove 3 more claims"
    with pytest.raises(NotAllowed, match="3 more claims"):
        cases.approve(k, "C1", H1, 1)


def test_approve_allowed_after_confirm_edit_or_remove(k):
    cases.open_case(k, "C1", H1, 0)
    a, b, d = claim_ids(k)
    cases.confirm_claim(k, "C1", H1, 1, a)
    cases.edit_claim(k, "C1", H1, 2, b, "  better wording  ")
    assert cases.can_approve(k, "C1") == (False, "Confirm, edit or remove 1 more claim")
    cases.remove_claim(k, "C1", H1, 3, d)
    assert cases.can_approve(k, "C1")[0]
    cases.approve(k, "C1", H1, 4)
    r = row(k)
    assert (r["state"], r["owner_id"], r["handed_over_at"]) == ("handed_over", "S1", "2026-11-10T12:30:00")


def test_approve_needs_a_live_claim_and_a_department(k):
    cases.open_case(k, "C1", H1, 0)
    v = 1
    for cid in claim_ids(k):
        cases.remove_claim(k, "C1", H1, v, cid)
        v += 1
    assert cases.can_approve(k, "C1") == (False, "Add at least one claim")
    k.execute("UPDATE cases SET department=NULL")
    k.commit()
    assert cases.can_approve(k, "C1") == (False, "Set the department first")


def test_unsupported_claim_cannot_be_confirmed_but_can_be_edited(k):
    cases.open_case(k, "C1", H1, 0)
    c3 = claim_ids(k)[2]
    with pytest.raises(NotAllowed, match="no matching quote"):
        cases.confirm_claim(k, "C1", H1, 1, c3)
    cases.edit_claim(k, "C1", H1, 1, c3, "my words")
    r = k.execute("SELECT * FROM claims WHERE id=?", (c3,)).fetchone()
    assert (r["status"], r["text"], r["original_text"]) == ("edited", "my words", "claim 3")


def test_edit_keeps_first_original_and_limits_length(k):
    cases.open_case(k, "C1", H1, 0)
    c1 = claim_ids(k)[0]
    cases.edit_claim(k, "C1", H1, 1, c1, "one")
    cases.edit_claim(k, "C1", H1, 2, c1, "two")
    assert k.execute("SELECT original_text FROM claims WHERE id=?", (c1,)).fetchone()[0] == "claim 1"
    for bad in ("", "   ", "x" * 601):
        with pytest.raises(NotAllowed):
            cases.edit_claim(k, "C1", H1, 3, c1, bad)
    cases.edit_claim(k, "C1", H1, 3, c1, "x" * 600)


def test_claim_of_another_case_refused(k):
    cases.open_case(k, "C1", H1, 0)
    k.execute("INSERT INTO claims(case_id, seq, text, supported, status) VALUES ('C2',1,'z',1,'draft')")
    k.commit()
    other = k.execute("SELECT id FROM claims WHERE case_id='C2'").fetchone()[0]
    with pytest.raises(NotAllowed):
        cases.confirm_claim(k, "C1", H1, 1, other)


def test_add_claim_is_edited_status(k):
    cases.open_case(k, "C1", H1, 0)
    cases.add_claim(k, "C1", H1, 1, " by hand ")
    r = k.execute("SELECT * FROM claims WHERE case_id='C1' ORDER BY seq DESC").fetchone()
    assert (r["seq"], r["status"], r["text"], r["original_text"]) == (4, "edited", "by hand", None)


def test_reject_needs_reason_and_keeps_state(k):
    cases.open_case(k, "C1", H1, 0)
    with pytest.raises(NotAllowed, match="at least 10"):
        cases.reject_draft(k, "C1", H1, 1, "too short")
    with pytest.raises(NotAllowed, match="500"):
        cases.reject_draft(k, "C1", H1, 1, "x" * 501)
    cases.reject_draft(k, "C1", H1, 1, "Summary missed the dispute")
    r = row(k)
    assert (r["state"], r["draft_state"]) == ("in_review", "rejected")
    assert {x[0] for x in k.execute("SELECT status FROM claims")} == {"removed"}
    assert k.execute("SELECT COUNT(*) FROM events WHERE kind!='opened'").fetchone()[0] == 0
    with pytest.raises(NotAllowed):
        cases.reject_draft(k, "C1", H1, 2, "Summary missed the dispute")


def test_handover_only_required_fields(k):
    cases.open_case(k, "C1", H1, 0)
    with pytest.raises(NotAllowed, match="not part of"):
        cases.set_handover(k, "C1", H1, 1, {"monthly_income": "1"})
    cases.set_handover(k, "C1", H1, 1, {"merchant_name": " Shop "})
    assert json.loads(row(k)["handover_json"]) == {"merchant_name": "Shop"}
    with pytest.raises(NotAllowed):
        cases.set_handover(k, "C1", H1, 2, {"merchant_name": "x" * 501})


def test_incomplete_handover_is_sent_and_logged(k):
    cases.open_case(k, "C1", H1, 0)
    a, b, d = claim_ids(k)
    v = 1
    for f, cid in ((cases.confirm_claim, a), (cases.confirm_claim, b), (cases.remove_claim, d)):
        f(k, "C1", H1, v, cid)
        v += 1
    cases.set_handover(k, "C1", H1, v, {"merchant_name": "Shop"})
    cases.approve(k, "C1", H1, v + 1)
    d = json.loads(k.execute("SELECT detail_json FROM audit WHERE action='approve'").fetchone()[0])
    assert d["incomplete"] is True and "police_reference" in d["missing"]
    assert row(k)["state"] == "handed_over"


def test_complete_handover_logged_complete(k):
    ready(k)
    cases.approve(k, "C1", H1, ver(k))
    d = json.loads(k.execute("SELECT detail_json FROM audit WHERE action='approve'").fetchone()[0])
    assert d["incomplete"] is False and d["missing"] == []


def test_department_without_specialist_keeps_handler(k):
    k.execute("UPDATE cases SET department='General service'")
    k.commit()
    cases.open_case(k, "C1", H1, 0)
    v = 1
    for cid in claim_ids(k):
        cases.remove_claim(k, "C1", H1, v, cid)
        v += 1
    cases.add_claim(k, "C1", H1, v, "mine")
    cases.approve(k, "C1", H1, v + 1)
    assert row(k)["owner_id"] == "H1"


def test_accept_only_by_specialist_of_that_department(k):
    ready(k)
    cases.approve(k, "C1", H1, ver(k))
    with pytest.raises(NotAllowed, match="Fraud claims"):
        cases.accept(k, "C1", S2, ver(k))
    with pytest.raises(NotAllowed):
        cases.accept(k, "C1", H1, ver(k))
    cases.accept(k, "C1", S1, ver(k))
    r = row(k)
    assert (r["state"], r["accepted_at"]) == ("accepted", "2026-11-10T12:30:00")
    ev = k.execute("SELECT kind, actor_id FROM events ORDER BY id DESC").fetchone()
    assert (ev["kind"], ev["actor_id"]) == ("accepted", "S1")


def test_first_return_goes_to_handler_second_to_team_lead(k):
    ready(k)
    cases.approve(k, "C1", H1, ver(k))
    with pytest.raises(NotAllowed, match="at least 10"):
        cases.return_case(k, "C1", S1, ver(k), "no")
    cases.return_case(k, "C1", S1, ver(k), "Police reference missing")
    r = row(k)
    assert (r["state"], r["return_count"], r["owner_id"]) == ("returned", 1, "H1")
    assert r["urgent"] == 1  # returned before
    cases.open_case(k, "C1", H1, ver(k))
    cases.approve(k, "C1", H1, ver(k))
    assert row(k)["owner_id"] == "S1"
    cases.return_case(k, "C1", S1, ver(k), "Still no police reference")
    r = row(k)
    assert (r["return_count"], r["owner_id"]) == (2, "T1")
    cases.open_case(k, "C1", T1, ver(k))
    cases.approve(k, "C1", T1, ver(k))
    assert row(k)["owner_id"] == "T1"


def test_specialist_cannot_work_the_case(k):
    with pytest.raises(NotAllowed):
        cases.open_case(k, "C1", S1, 0)
    with pytest.raises(NotAllowed):
        cases.add_claim(k, "C1", S1, 0, "x")


def test_wrong_state_refused(k):
    with pytest.raises(NotAllowed, match="in review"):
        cases.approve(k, "C1", H1, 0)
    with pytest.raises(NotAllowed):
        cases.accept(k, "C1", S1, 0)


def test_assign_rules(k):
    with pytest.raises(NotAllowed, match="already has an owner"):
        cases.assign(k, "C1", H2, 0, "H2")
    k.execute("UPDATE cases SET owner_id=NULL")
    k.commit()
    with pytest.raises(NotAllowed, match="yourself"):
        cases.assign(k, "C1", H2, 0, "H1")
    cases.assign(k, "C1", H2, 0, "H2")
    assert row(k)["owner_id"] == "H2"
    cases.assign(k, "C1", T1, 1, "H3")
    assert row(k)["owner_id"] == "H3"
    with pytest.raises(NotAllowed, match="No such"):
        cases.assign(k, "C1", T1, 2, "ZZ")
    with pytest.raises(NotAllowed):
        cases.assign(k, "C1", S1, 2, "S1")


def test_set_urgent_overrides_and_needs_reason(k):
    with pytest.raises(NotAllowed, match="at least 10"):
        cases.set_urgent(k, "C1", H1, 0, True, "x")
    cases.set_urgent(k, "C1", H1, 0, True, "Customer is vulnerable")
    r = row(k)
    assert (r["urgent"], r["urgent_manual"]) == (1, 1)
    cases.set_urgent(k, "C1", H1, 1, False, "Raised in error here")
    r = row(k)
    assert (r["urgent"], r["urgent_manual"]) == (0, 0)


def test_set_department(k):
    cases.set_department(k, "C1", H1, 0, "Bereavement")
    assert row(k)["department"] == "Bereavement"
    with pytest.raises(NotAllowed, match="Choose a department"):
        cases.set_department(k, "C1", H1, 1, "Nonsense")
    k.execute("UPDATE cases SET state='handed_over'")
    k.commit()
    with pytest.raises(NotAllowed):
        cases.set_department(k, "C1", H1, 1, "Fraud claims")


def test_unmask_is_audit_only(k):
    n = audits(k)
    cases.unmask(k, "C1", H1, 0, "Need the account number to verify")
    assert audits(k) == n + 1 and ver(k) == 0
    with pytest.raises(NotAllowed, match="at least 10"):
        cases.unmask(k, "C1", H1, 0, "short")
    with pytest.raises(StaleCase):
        cases.unmask(k, "C1", H1, 5, "Need the account number to verify")


def test_stale_version_raises_and_changes_nothing(k):
    cases.open_case(k, "C1", H1, 0)
    n_a, n_e, before = audits(k), k.execute("SELECT COUNT(*) FROM events").fetchone()[0], dict(row(k))
    with pytest.raises(StaleCase, match="Reload to see the latest"):
        cases.add_claim(k, "C1", H2, 0, "late")
    assert (audits(k), k.execute("SELECT COUNT(*) FROM events").fetchone()[0], dict(row(k))) == (n_a, n_e, before)
    assert k.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 3


def test_every_action_adds_one_audit_row_and_chain_verifies(k):
    calls = [lambda v: cases.open_case(k, "C1", H1, v),
             lambda v: cases.confirm_claim(k, "C1", H1, v, claim_ids(k)[0]),
             lambda v: cases.edit_claim(k, "C1", H1, v, claim_ids(k)[1], "e"),
             lambda v: cases.remove_claim(k, "C1", H1, v, claim_ids(k)[2]),
             lambda v: cases.add_claim(k, "C1", H1, v, "a"),
             lambda v: cases.set_handover(k, "C1", H1, v, FRAUD),
             lambda v: cases.set_urgent(k, "C1", H1, v, True, "A good reason here"),
             lambda v: cases.set_department(k, "C1", H1, v, "Fraud claims"),
             lambda v: cases.approve(k, "C1", H1, v),
             lambda v: cases.accept(k, "C1", S1, v)]
    for f in calls:
        n, v = audits(k), ver(k)
        f(v)
        assert audits(k) == n + 1 and ver(k) == v + 1
    assert audit.verify_chain(k) is None


def test_failed_action_rolls_back_everything(k):
    cases.open_case(k, "C1", H1, 0)
    n = audits(k)
    with pytest.raises(NotAllowed):
        cases.reject_draft(k, "C1", H1, 1, "short")
    assert audits(k) == n and not k.in_transaction


def test_next_action_lines(k):
    assert cases.next_action(k, "C1", "handler") == "Open the case to start the review"
    cases.open_case(k, "C1", H1, 0)
    assert cases.next_action(k, "C1", "handler") == "Confirm, edit or remove 3 more claims"
    assert cases.next_action(k, "C1", "specialist") == "Nothing for you to do yet"
    k.execute("UPDATE cases SET state='handed_over'")
    k.commit()
    assert cases.next_action(k, "C1", "specialist") == "Accept, or return with a reason"
    assert cases.next_action(k, "C1", "handler") == "Waiting for Fraud claims to accept"
