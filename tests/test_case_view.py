import json
import re
import sqlite3
from pathlib import Path

import pytest

REC = Path(__file__).resolve().parents[1] / "data" / "recordings"
SCRIPT = "<script>alert(1)</script>"
ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;"


@pytest.fixture(scope="module")
def big_db_file(tmp_path_factory):
    """The 1,600-case database the recordings were made for."""
    from workbench.config import load_config
    from workbench.db import connect, init_db
    from workbench.generate import generate
    path = tmp_path_factory.mktemp("bigdb") / "workbench.db"
    c = connect(path)
    init_db(c)
    generate(c, n=1600, seed=7, cfg=load_config())
    c.execute("UPDATE cases SET department = 'Fraud claims' WHERE department IS NULL")  # as the classify step would, so startup loads drafts
    c.commit()
    c.close()
    return path


@pytest.fixture
def app_db(big_db_file, tmp_path):
    import shutil
    from workbench import audit
    dst = tmp_path / "workbench.db"
    shutil.copy(big_db_file, dst)
    yield dst
    audit.set_clock(None)


def sql(db, q, *a, write=False):
    c = sqlite3.connect(db)
    try:
        r = c.execute(q, a).fetchall()
        if write:
            c.commit()
        return r
    finally:
        c.close()


def pick(db, where="state = 'in_review'"):
    """A case that has a recording and a department, forced into the wanted state (the test database is a private copy)."""
    state = re.search(r"'(\w+)'", where).group(1)
    ids = [r[0] for r in sql(db, "SELECT id FROM cases WHERE 1=1 ORDER BY id")]
    cid = next(i for i in ids if (REC / f"{i}.json").exists())
    sql(db, "UPDATE cases SET state=?, department='Fraud claims', owner_id='H1', return_count=0 WHERE id=?", state, cid, write=True)
    return cid


def ver(db, cid):
    return sql(db, "SELECT version FROM cases WHERE id=?", cid)[0][0]


def post(client, db, cid, path, **data):
    return client.post(f"/cases/{cid}/{path}", data={"version": ver(db, cid), "step": 1, **data})


def test_unknown_and_malformed_ids_are_404(client):
    for cid in ("AB-2026-99999", "nope", "AB-2026-1<script>"):
        r = client.get(f"/cases/{cid}")
        assert r.status_code == 404 and "Case not found" in r.text and "Traceback" not in r.text


def test_page_shows_no_personal_data_and_sets_last_case(client, app_db):
    cid = pick(app_db)
    r = client.get(f"/cases/{cid}")
    assert r.status_code == 200 and cid in r.text
    cust = json.loads(sql(app_db, "SELECT customer_json FROM cases WHERE id=?", cid)[0][0])
    for k in ("name", "account_number", "sort_code", "email", "phone", "address"):
        assert cust[k] not in r.text, k
    assert client.cookies.get("last_case") == cid
    assert 'href="/cases/' + cid + '"' in client.get("/queue").text  # the nav link now points at it


def test_approve_disabled_while_draft_claim_remains(client, app_db):
    cid = pick(app_db)
    html = client.get(f"/cases/{cid}?step=3").text
    assert re.search(r"<button[^>]*primary[^>]*disabled", html)
    assert "Confirm, edit or remove" in html


def test_claim_labels_and_no_confirm_on_unsupported(client, app_db):
    cid = pick(app_db)
    client.get(f"/cases/{cid}")
    sql(app_db, "UPDATE claims SET supported = 0 WHERE id = (SELECT MIN(id) FROM claims WHERE case_id=?)", cid, write=True)
    html = client.get(f"/cases/{cid}").text
    assert "Quote not found in the note" in html
    first = html.split('<li class="claim"')[1].split("</li>")[0]
    assert "/confirm" not in first and "Confirm" not in first
    assert "AI draft" in html and html.count("AI draft") == 1


def test_quote_highlight_is_escaped_not_html(client, app_db):
    cid = pick(app_db)
    client.get(f"/cases/{cid}")
    nid = sql(app_db, "SELECT note_id FROM claims WHERE case_id=? AND supported=1 LIMIT 1", cid)[0][0]
    sql(app_db, "UPDATE notes SET body = body || ? WHERE id=?", SCRIPT, nid, write=True)
    html = client.get(f"/cases/{cid}").text
    assert "<script>alert" not in html and "<mark" in html


def test_confirm_all_then_approve_by_hand_path(client, app_db):
    cid = pick(app_db)
    client.get(f"/cases/{cid}")
    for (claim,) in sql(app_db, "SELECT id FROM claims WHERE case_id=? AND status='draft'", cid):
        r = post(client, app_db, cid, f"claims/{claim}/confirm", all=0)
        if sql(app_db, "SELECT supported FROM claims WHERE id=?", claim)[0][0]:
            assert r.status_code == 200 and 'id="case"' in r.text
        else:
            assert r.status_code == 403
            post(client, app_db, cid, f"claims/{claim}/remove")
    assert sql(app_db, "SELECT COUNT(*) FROM claims WHERE case_id=? AND status='draft'", cid) == [(0,)]


def test_stale_version_is_409_with_message(client, app_db):
    cid = pick(app_db)
    r = client.post(f"/cases/{cid}/claims", data={"version": ver(app_db, cid) + 5, "text": "Something"})
    assert r.status_code == 409 and "changed since you opened it" in r.text and "Traceback" not in r.text


def test_non_htmx_post_redirects_and_htmx_swaps(client, app_db):
    cid = pick(app_db)
    r = client.post(f"/cases/{cid}/claims", data={"version": ver(app_db, cid), "text": "A claim added by hand"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith(f"/cases/{cid}")
    r = client.post(f"/cases/{cid}/claims", data={"version": ver(app_db, cid), "text": "Another by hand"}, headers={"HX-Request": "true"})
    assert r.status_code == 200 and "<html" not in r.text and r.text.lstrip().startswith('<div id="case"')


def test_by_hand_case_can_be_approved(client, app_db):
    cid = pick(app_db)
    sql(app_db, "UPDATE cases SET draft_state='rejected' WHERE id=?", cid, write=True)
    sql(app_db, "DELETE FROM claims WHERE case_id=?", cid, write=True)
    html = client.get(f"/cases/{cid}").text
    assert "Complete the summary by hand" in html
    assert post(client, app_db, cid, "claims", text="The customer reports a problem.").status_code == 200
    dept = sql(app_db, "SELECT department FROM cases WHERE id=?", cid)[0][0]
    from workbench.config import load_config
    names = load_config()["departments"][dept]["required_fields"]
    r = post(client, app_db, cid, "handover", **{"f_" + n: "x" for n in names})
    assert r.status_code == 200
    assert post(client, app_db, cid, "approve").status_code == 200
    assert sql(app_db, "SELECT state FROM cases WHERE id=?", cid) == [("handed_over",)]


def test_no_department_shows_by_hand_message(client, app_db):
    cid = pick(app_db)
    sql(app_db, "UPDATE cases SET department = NULL WHERE id=?", cid, write=True)
    html = client.get(f"/cases/{cid}").text
    state = sql(app_db, "SELECT state FROM cases WHERE id=?", cid)[0][0]
    assert "No department yet" in html and ("by hand" in html if state in ("in_review", "returned") else "Start review" in html if state == "new" else True)


def test_reason_is_escaped_on_case_page_and_trail(client, app_db):
    cid = pick(app_db)
    r = client.post(f"/cases/{cid}/unmask", data={"version": ver(app_db, cid), "reason": SCRIPT})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert SCRIPT not in r.text and ESCAPED in r.text
    assert ESCAPED in client.get(f"/cases/{cid}").text
    assert sql(app_db, "SELECT action FROM audit WHERE case_id=? ORDER BY id DESC LIMIT 1", cid) == [("unmask",)]


def test_unmask_needs_a_reason_and_is_not_cached_normally(client, app_db):
    cid = pick(app_db)
    r = client.post(f"/cases/{cid}/unmask", data={"version": ver(app_db, cid), "reason": ""})
    assert r.status_code == 403 and "Enter a reason" in r.text
    assert "no-store" not in client.get(f"/cases/{cid}").headers.get("cache-control", "")


def test_reject_needs_reason_and_keeps_confirmed(client, app_db):
    cid = pick(app_db)
    client.get(f"/cases/{cid}")
    assert "Removes only the claims you have not yet confirmed or edited." in client.get(f"/cases/{cid}").text
    r = post(client, app_db, cid, "reject", reason="")
    assert r.status_code == 403 and "Enter a reason" in r.text
    first = sql(app_db, "SELECT id FROM claims WHERE case_id=? AND supported=1 LIMIT 1", cid)[0][0]
    post(client, app_db, cid, f"claims/{first}/confirm")
    r = post(client, app_db, cid, "reject", reason="The draft misses the point.")
    assert r.status_code == 200
    left = sql(app_db, "SELECT status FROM claims WHERE case_id=? AND status != 'removed'", cid)
    assert left == [("confirmed",)]
    assert sql(app_db, "SELECT draft_state FROM cases WHERE id=?", cid) == [("rejected",)]


def test_specialist_sees_accept_and_return_not_approve(client, app_db):
    cid = pick(app_db, "state = 'handed_over'")
    client.cookies.set("role", "specialist")
    client.cookies.set("staff_id", "S1")
    html = client.get(f"/cases/{cid}").text
    assert re.search(r'<button[^>]*primary[^>]*>Accept</button>', html) and "Return to the handler" in html and "Approve and send</button>" not in html


def test_urgent_and_department_changes_go_through_cases(client, app_db):
    cid = pick(app_db)
    r = post(client, app_db, cid, "urgent", urgent="1", reason="")
    assert r.status_code == 403 and "Enter a reason" in r.text
    r = post(client, app_db, cid, "urgent", urgent="1", reason="Customer is vulnerable.")
    assert r.status_code == 200 and sql(app_db, "SELECT urgent_manual FROM cases WHERE id=?", cid) == [(1,)]
    r = post(client, app_db, cid, "department", department="Nowhere")
    assert r.status_code == 403 and "Choose a department" in r.text


def test_new_case_offers_start_review(client, app_db):
    cid = pick(app_db, "state = 'new'")
    assert "Start review" in client.get(f"/cases/{cid}").text
    r = client.post(f"/cases/{cid}/open", data={"version": ver(app_db, cid)})
    assert r.status_code == 200 and sql(app_db, "SELECT state FROM cases WHERE id=?", cid) == [("in_review",)]




# ---- fix round 1 ----
HX = {"HX-Request": "true"}


def counts(db):
    return sql(db, "SELECT (SELECT COUNT(*) FROM claims), (SELECT COUNT(*) FROM audit), (SELECT COUNT(*) FROM events), "
                   "(SELECT group_concat(draft_state) FROM cases)")


def as_role(client, role, sid):
    client.cookies.set("role", role)
    client.cookies.set("staff_id", sid)


def test_get_writes_nothing_and_startup_loaded_the_claims(client, app_db):
    cid = pick(app_db)
    assert sql(app_db, "SELECT COUNT(*) FROM claims WHERE case_id=?", cid)[0][0] > 0  # loaded when the app started
    assert sql(app_db, "SELECT draft_state FROM cases WHERE id=?", cid) == [("available",)]
    before = counts(app_db)
    for u in (f"/cases/{cid}", f"/cases/{cid}?all=1", "/cases/AB-2026-99999"):
        client.get(u)
    assert counts(app_db) == before


def test_case_id_uses_fullmatch_and_vanished_case_gets_small_fragment(client, app_db):
    assert client.get("/cases/AB-2026-00001%0A").status_code == 404
    r = client.post("/cases/AB-2026-99999/approve", data={"version": 0}, headers=HX)
    assert r.status_code == 404 and "<html" not in r.text and "Case not found" in r.text
    r = client.post("/cases/nope/approve", data={"version": 0}, headers=HX)
    assert r.status_code == 404 and "<html" not in r.text
    r = client.post("/cases/nope/handover", data={"version": 0}, headers=HX)
    assert r.status_code == 404 and "<html" not in r.text


def test_page_has_live_region_outside_case_history_off_and_hint_dismiss(client, app_db):
    cid = pick(app_db)
    html = client.get(f"/cases/{cid}").text
    assert html.index('id="live"') < html.index('id="case"') and 'role="status"' in html.split('id="live"')[0][-80:]
    assert 'hx-history="false"' in html
    assert "New here?" not in html  # no first-visit banner: Help is one click away


def test_no_deadline_strip_on_case_and_not_found_but_on_queue(client, app_db):
    cid = pick(app_db)
    assert 'class="strip"' not in client.get(f"/cases/{cid}").text
    assert 'class="strip"' not in client.get("/cases/AB-2026-99999").text
    assert 'class="strip"' in client.get("/queue").text


def test_header_prints_no_deadline_reason_and_set_by_hand_only_when_set(client, app_db):
    cid = pick(app_db)
    sql(app_db, "UPDATE cases SET urgent=1, urgent_manual=NULL, deadline='2026-10-01' WHERE id=?", cid, write=True)
    head = client.get(f"/cases/{cid}").text.split('class="case-head"')[1].split("</header>")[0]
    assert "Deadline within" not in head and "Set by hand" not in head and "Urgent" in head
    sql(app_db, "UPDATE cases SET urgent_manual=1 WHERE id=?", cid, write=True)
    head = client.get(f"/cases/{cid}").text.split('class="case-head"')[1].split("</header>")[0]
    assert "Set by hand" in head


def test_nav_names_the_case_being_viewed_without_cookie(client, app_db):
    cid = pick(app_db)
    nav = client.get(f"/cases/{cid}").text.split("<nav")[1].split("</nav>")[0]
    assert f'href="/cases/{cid}"' in nav


def test_nav_shows_case_id_after_visit(client, app_db):
    cid = pick(app_db)
    client.get(f"/cases/{cid}")
    nav = client.get("/queue").text.split("<nav")[1].split("</nav>")[0]
    assert f'href="/cases/{cid}"' in nav


def test_specialist_decide_card_has_no_claim_repeat_and_bar_has_link(client, app_db):
    cid = pick(app_db, "state = 'handed_over'")
    as_role(client, "specialist", "S1")
    html = client.get(f"/cases/{cid}").text
    text = sql(app_db, "SELECT text FROM claims WHERE case_id=? ORDER BY seq LIMIT 1", cid)[0][0]
    assert html.count(text) == 1
    assert re.search(r'<form[^>]*action="/cases/[^"]+/accept"', html)
    bar = html.split('class="bottom-bar"')[1]
    assert 'href="#decide"' in bar and "Go to decide" in bar


def test_other_department_specialist_gets_one_plain_line_and_no_buttons(client, app_db):
    cid = pick(app_db, "state = 'handed_over'")
    sql(app_db, "UPDATE cases SET department='Data protection' WHERE id=?", cid, write=True)
    as_role(client, "specialist", "S1")
    html = client.get(f"/cases/{cid}").text
    assert "Only the Data protection specialist can accept or return this." in html
    assert "/accept" not in html and "Return to the handler" not in html


def test_can_decide_helper(app_db):
    from workbench import cases
    from workbench.db import connect
    cid = pick(app_db, "state = 'handed_over'")
    c = connect(app_db)
    try:
        assert cases.can_decide(c, cid, cases.Actor("S1", "specialist"))[0] is True
        ok, msg = cases.can_decide(c, cid, cases.Actor("S2", "specialist"))
        assert ok is False and msg == "Only the Fraud claims specialist can accept or return this."
    finally:
        c.close()


def test_handover_money_fields_show_pound_and_mark_takes_focus(client, app_db):
    cid = pick(app_db)
    html = client.get(f"/cases/{cid}?step=2").text
    assert re.search(r'<span class="money">£</span>\s*<input name="f_amount_disputed"', html)
    assert '<mark id="src-1" tabindex="-1"' in client.get(f"/cases/{cid}").text


def test_team_lead_may_unmask_and_wrong_department_specialist_may_not(client, app_db):
    cid = pick(app_db)
    as_role(client, "team_lead", "T1")
    r = client.post(f"/cases/{cid}/unmask", data={"version": ver(app_db, cid), "reason": "Checking the original wording."})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    cid2 = pick(app_db, "state = 'handed_over'")
    sql(app_db, "UPDATE cases SET department='Data protection' WHERE id=?", cid2, write=True)
    as_role(client, "specialist", "S1")
    r = client.post(f"/cases/{cid2}/unmask", data={"version": ver(app_db, cid2), "reason": "Checking the original wording."})
    assert r.status_code == 403 and "Only the Data protection specialist" in r.text


def test_case_post_with_bad_origin_is_403(client, app_db):
    cid = pick(app_db)
    r = client.post(f"/cases/{cid}/approve", data={"version": ver(app_db, cid)}, headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
    assert sql(app_db, "SELECT state FROM cases WHERE id=?", cid) == [("in_review",)]


def test_zero_claims_none_and_invalid_render_by_hand_path(client, app_db):
    for state, words in (("none", "No draft recorded"), ("invalid", "could not be read")):
        cid = pick(app_db)
        sql(app_db, "DELETE FROM claims WHERE case_id=?", cid, write=True)
        sql(app_db, "UPDATE cases SET draft_state=? WHERE id=?", state, cid, write=True)
        html = client.get(f"/cases/{cid}").text
        assert words in html and "Complete the summary by hand" in html and "<summary>Add a claim" in html
        assert post(client, app_db, cid, "claims", text="By hand.").status_code == 200


def test_split_note_units():
    from workbench.case_view import split_note
    assert split_note("hello world again", [(1, "hello world"), (2, "world again")]) == [("hello world", 1), (" again", None)]
    assert split_note("so so so", [(1, "so")]) == [("so", 1), (" so so", None)]
    assert split_note("cost a+b (c)? now", [(1, "a+b (c)?")]) == [("cost ", None), ("a+b (c)?", 1), (" now", None)]
    assert split_note("nothing here", [(1, "absent quote")]) == [("nothing here", None)]
    assert split_note("A  b\nc", [(1, "a b c")]) == [("A  b\nc", 1)]


def test_money_text_formats_numbers_and_leaves_other_text_alone():
    from workbench.case_view import money_text
    assert money_text("2318.11") == ("2,318.11", True)
    assert money_text("£2,318.1") == ("2,318.10", True)  # a leading pound sign is not doubled
    assert money_text("about two grand") == ("about two grand", False)  # as typed, no pound sign
    assert money_text("") == ("", False)


def test_money_field_shows_separators_and_no_pound_for_text(client, app_db):
    cid = pick(app_db)
    sql(app_db, "UPDATE cases SET handover_json=? WHERE id=?", '{"amount_disputed": "2318.11"}', cid, write=True)
    assert 'value="2,318.11"' in client.get(f"/cases/{cid}?step=2").text
    sql(app_db, "UPDATE cases SET handover_json=? WHERE id=?", '{"amount_disputed": "a lot"}', cid, write=True)
    html = client.get(f"/cases/{cid}?step=2").text
    assert 'value="a lot"' in html and not re.search(r'<span class="money">£</span>\s*<input name="f_amount_disputed"', html)


def test_restart_adds_no_claims_for_rejected_or_emptied_drafts(big_db_file, tmp_path):
    import shutil
    from workbench.app import create_app
    db = tmp_path / "w.db"
    shutil.copy(big_db_file, db)
    create_app(str(db), models_dir=None)  # first start loads every recording
    ids = [r[0] for r in sql(db, "SELECT id FROM cases ORDER BY id") if (REC / f"{r[0]}.json").exists()][:2]
    sql(db, "DELETE FROM claims WHERE case_id IN (?,?)", *ids, write=True)
    sql(db, "UPDATE cases SET draft_state='rejected' WHERE id=?", ids[0], write=True)
    sql(db, "UPDATE cases SET draft_state='available' WHERE id=?", ids[1], write=True)  # every claim removed, row state kept
    sql(db, "INSERT INTO claims(case_id, seq, text, status) VALUES (?,1,'gone','removed')", ids[1], write=True)
    before = sql(db, "SELECT COUNT(*) FROM claims")
    create_app(str(db), models_dir=None)
    assert sql(db, "SELECT COUNT(*) FROM claims") == before


def test_department_set_after_startup_loads_the_draft(client, app_db):
    cid = pick(app_db)
    sql(app_db, "UPDATE cases SET department=NULL, draft_state='none' WHERE id=?", cid, write=True)
    sql(app_db, "DELETE FROM claims WHERE case_id=?", cid, write=True)
    assert post(client, app_db, cid, "department", department="Fraud claims").status_code == 200
    assert sql(app_db, "SELECT COUNT(*) FROM claims WHERE case_id=?", cid)[0][0] > 0


def test_404_fragment_takes_focus_and_bar_text_is_not_a_live_region(client, app_db):
    r = client.post("/cases/AB-2026-99999/approve", data={"version": 0}, headers=HX)
    assert 'id="case" tabindex="-1"' in r.text
    assert 'id="bar-text" role=' not in client.get(f"/cases/{pick(app_db)}").text


# ---- one-window: recent-case tabs, Previous and Next ----
def step_cases(html):
    return html.split('class="step-cases"')[1].split("</div>")[0]


def test_recent_tabs_newest_first_capped_and_cookie_checked(client, app_db):
    from workbench.views.case import recent_ids
    ids = [r[0] for r in sql(app_db, "SELECT id FROM cases ORDER BY id LIMIT 7")]
    assert recent_ids(f"nope.AB-2026-1<x>.{ids[1]}.{ids[0]}.{ids[1]}", ids[0]) == [ids[0], ids[1]]  # bad ids and repeats dropped
    for cid in ids[:6]:
        client.get(f"/cases/{cid}")
    assert client.cookies.get("recent") == ".".join(reversed(ids[1:6]))  # newest first, five kept
    html = client.get(f"/cases/{ids[3]}").text
    tabs = html.split('class="recent"')[1].split("</ul>")[0]
    assert re.findall(r'href="/cases/([^"]+)"', tabs) == [ids[3], ids[5], ids[4], ids[2], ids[1]]
    assert f'href="/cases/{ids[3]}" aria-current="true"' in tabs and 'class="dot st-' in tabs


def test_previous_and_next_follow_the_queue_order_of_the_persons_list(client, app_db):
    order = [r[0] for r in sql(app_db, "SELECT id FROM cases WHERE owner_id='H1' AND state != 'accepted' ORDER BY deadline, urgent DESC, id")]
    html = step_cases(client.get(f"/cases/{order[1]}").text)
    assert f'href="/cases/{order[0]}" rel="prev"' in html and f'href="/cases/{order[2]}" rel="next"' in html and f"2 of {len(order)}" in html
    other = sql(app_db, "SELECT id FROM cases WHERE owner_id != 'H1' OR owner_id IS NULL LIMIT 1")[0][0]
    html = step_cases(client.get(f"/cases/{other}").text)
    assert f'href="/cases/{order[0]}" rel="next"' in html and 'rel="prev"' not in html  # outside the list: Next goes to its first case
    as_role(client, "specialist", "S1")
    dept = sql(app_db, "SELECT department FROM staff WHERE id='S1'")[0][0]
    mine = [r[0] for r in sql(app_db, "SELECT id FROM cases WHERE state='handed_over' AND department=? ORDER BY deadline, urgent DESC, id", dept)]
    html = step_cases(client.get(f"/cases/{mine[-1]}").text)
    assert f"{len(mine)} of {len(mine)}" in html and '<span class="off">Next</span>' in html
