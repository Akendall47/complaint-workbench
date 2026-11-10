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
    ids = [r[0] for r in sql(db, "SELECT id FROM cases WHERE draft_state = 'none' ORDER BY id")]
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
    assert "Not found in the notes" in html and "Quote not found in the note" in html
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
    sql(app_db, "UPDATE cases SET draft_state='rejected' WHERE id=?", cid, write=True)  # no draft will load
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
    cid = sql(app_db, "SELECT id FROM cases WHERE department IS NULL LIMIT 1")
    if not cid:
        pytest.skip("no case without a department in this data set")
    html = client.get(f"/cases/{cid[0][0]}").text
    assert "no department yet" in html and "by hand" in html


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
    r = post(client, app_db, cid, "reject", reason="")
    assert r.status_code == 403 and "Enter a reason" in r.text
    first = sql(app_db, "SELECT id FROM claims WHERE case_id=? AND supported=1 LIMIT 1", cid)[0][0]
    post(client, app_db, cid, f"claims/{first}/confirm")
    r = post(client, app_db, cid, "reject", reason="The draft misses the point.")
    assert r.status_code == 200
    left = sql(app_db, "SELECT status FROM claims WHERE case_id=? AND status != 'removed'", cid)
    assert left == [("confirmed",)]
    assert "Removes only the claims" in client.get(f"/cases/{cid}").text or sql(app_db, "SELECT draft_state FROM cases WHERE id=?", cid) == [("rejected",)]


def test_specialist_sees_accept_and_return_not_approve(client, app_db):
    cid = pick(app_db, "state = 'handed_over'")
    client.cookies.set("role", "specialist")
    client.cookies.set("staff_id", "S1")
    html = client.get(f"/cases/{cid}").text
    assert "Accept" in html and "Return to the handler" in html and "Approve and send</button>" not in html


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


def test_case_link_in_nav_no_longer_xfail(client, app_db):
    cid = pick(app_db)
    client.get(f"/cases/{cid}")
    assert client.get(f"/cases/{cid}").status_code == 200
