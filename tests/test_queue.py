import re
import sqlite3

from fastapi.testclient import TestClient

from workbench.app import create_app


def rows(html):
    return re.findall(r'<tr class="case-row"[^>]*data-case="([^"]+)"[^>]*data-days="(-?\d+)"', html)


def sql(app_db, q, *a):
    c = sqlite3.connect(app_db)
    try:
        return c.execute(q, a).fetchall()
    finally:
        c.close()


def test_no_match_message_and_clear_link(app_db):
    c = sqlite3.connect(app_db)
    c.execute("DELETE FROM cases WHERE department = 'Bereavement' AND urgent = 1")
    c.commit()
    r = TestClient(create_app(str(app_db), models_dir=None), base_url="http://127.0.0.1:8000").get("/queue?department=Bereavement&urgent=1&due=past")
    assert r.status_code == 200
    assert "No cases match these filters" in r.text and "Clear filters" in r.text
    assert "<table" not in r.text


def test_first_row_has_smallest_days_left(client):
    found = rows(client.get("/queue?owner=all").text)
    days = [int(d) for _, d in found]
    assert days and days[0] == min(days) and days == sorted(days)
    assert days[0] < 0  # past deadline first


def test_sort_urgent_first_on_ties(client, app_db):
    ids = [i for i, _ in rows(client.get("/queue?owner=all").text)]
    want = [r[0] for r in sql(app_db, "SELECT id FROM cases WHERE state != 'accepted' ORDER BY deadline, urgent DESC, id LIMIT 50")]
    assert ids == want


def test_handler_default_is_own_cases(client, app_db):
    ids = {i for i, _ in rows(client.get("/queue").text)}
    mine = {r[0] for r in sql(app_db, "SELECT id FROM cases WHERE owner_id = 'H1' AND state != 'accepted'")}
    assert ids == mine and ids


def table(html):
    return html.split('id="preview"')[0]


def test_unassigned_rows_offer_assign(client):
    html = client.get("/queue?owner=unassigned").text
    assert rows(html) and table(html).count(">Assign to me<") == len(rows(html))
    assert ">Assign to me<" in html.split('id="preview"')[1]  # the preview of the first row offers it too
    assert ">Assign to me<" not in client.get("/queue").text


def test_fifty_rows_per_page(client):
    p1, p2 = rows(client.get("/queue?owner=all").text), rows(client.get("/queue?owner=all&page=2").text)
    assert len(p1) == 50 and p2 and not {i for i, _ in p1} & {i for i, _ in p2}
    assert client.get("/queue?owner=all&page=abc").status_code == 200
    assert client.get("/queue?owner=all&page=9999").status_code == 200


def test_filters_narrow_rows(client, app_db):
    want = {r[0] for r in sql(app_db, "SELECT id FROM cases WHERE department='Fraud claims' AND state='in_review'")}
    got = {i for i, _ in rows(client.get("/queue?owner=all&department=Fraud+claims&state=in_review").text)}
    assert got == want
    assert client.get("/queue?owner=zzz&due=zzz&urgent=x&department=%27%3B--").status_code == 200


def test_no_details_row(client):
    first = rows(client.get("/queue?owner=all").text)[0][0]
    html = client.get(f"/queue?owner=all&expand={first}").text
    assert "detail-row" not in html and ">Details<" not in html


def test_assign_to_me_and_stale(client, app_db):
    cid, ver = sql(app_db, "SELECT id, version FROM cases WHERE owner_id IS NULL AND state != 'accepted' LIMIT 1")[0]
    r = client.post(f"/cases/{cid}/assign", data={"version": ver, "next": "/queue?owner=unassigned"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/queue?owner=unassigned"
    assert sql(app_db, "SELECT owner_id FROM cases WHERE id=?", cid) == [("H1",)]
    assert sql(app_db, "SELECT action FROM audit ORDER BY id DESC LIMIT 1") == [("assign",)]
    r = client.post(f"/cases/{cid}/assign", data={"version": ver, "next": "/queue"})  # stale
    assert r.status_code == 409 and "changed since you opened it" in r.text and "Traceback" not in r.text
    r = client.post("/cases/NOPE/assign", data={"version": 0, "next": "http://evil.example"})
    assert r.status_code == 403 and "does not exist" in r.text


def test_assign_bad_version_is_plain_message(client):
    r = client.post("/cases/AB-2026-00001/assign", data={"version": "abc", "next": "/queue"})
    assert r.status_code == 403 and "not valid" in r.text and "Traceback" not in r.text


def test_load_more_returns_the_next_rows_and_a_new_load_more_row(client):
    first = rows(client.get("/queue?owner=all").text)
    r = client.get("/queue/more?owner=all&page=2", headers={"HX-Request": "true"})
    nxt = rows(r.text)
    assert r.status_code == 200 and "<html" not in r.text and len(nxt) == 50 and not {i for i, _ in first} & {i for i, _ in nxt}
    assert 'hx-get="/queue/more?owner=all&amp;page=3"' in r.text and 'href="/queue?owner=all&amp;page=3"' in r.text
    assert 'id="shown" hx-swap-oob="true">Showing 100 of' in r.text


def test_first_row_is_previewed_and_next_case_is_the_second_row(client):
    html = client.get("/queue?owner=all").text
    (a, _), (b, _) = rows(html)[:2]
    pane = html.split('id="preview"')[1]
    assert re.search(rf'id="pk-{a}"[^>]* checked', table(html))
    assert f'href="/cases/{a}"' in pane and ">Open case<" in pane
    assert f'href="/queue/preview/{b}?owner=all"' in pane and ">Next case<" in pane


def test_preview_fragment_and_full_page_fallback(client):
    ids = [i for i, _ in rows(client.get("/queue?owner=all").text)]
    r = client.get(f"/queue/preview/{ids[1]}?owner=all", headers={"HX-Request": "true", "HX-Trigger": f"pk-{ids[1]}"})
    assert r.status_code == 200 and r.text.lstrip().startswith("<section") and "hx-swap-oob" not in r.text
    assert f"/queue/preview/{ids[2]}?owner=all" in r.text
    r = client.get(f"/queue/preview/{ids[1]}?owner=all", headers={"HX-Request": "true"})  # Next case: the row selection moves too
    assert re.search(rf'id="pk-{ids[1]}"[^>]* checked hx-swap-oob="true"', r.text)
    full = client.get(f"/queue/preview/{ids[1]}?owner=all").text
    assert "<html" in full and re.search(rf'id="pk-{ids[1]}"[^>]* checked', full) and not re.search(rf'id="pk-{ids[0]}"[^>]* checked', full)
    assert client.get("/queue/preview/AB-2026-99999").status_code == 404
    assert client.get("/queue/preview/nope", headers={"HX-Request": "true"}).status_code == 404


def test_preview_says_what_is_left_to_do(client, app_db):
    cid = sql(app_db, "SELECT id FROM cases WHERE state = 'new' AND owner_id IS NULL LIMIT 1")[0][0]
    go = lambda: client.get(f"/queue/preview/{cid}?owner=all", headers={"HX-Request": "true"}).text  # noqa: E731
    for words in ("Needs routing", "Received", "AI summary", "No draft yet", "Last note", ">Assign to me<"):
        assert words in go(), words
    c = sqlite3.connect(app_db)
    c.execute("UPDATE cases SET department = 'Fraud claims', handover_json = '{}' WHERE id = ?", (cid,))
    c.commit()
    pane = go()
    assert "Fraud claims <span class=\"muted\">set by the model</span>" in pane and "Missing Amount disputed, Date of transaction" in pane


def test_specialist_never_sees_assign(client):
    client.cookies.update({"role": "specialist", "staff_id": "S1"})
    html = client.get("/queue?owner=unassigned").text
    assert rows(html) and ">Assign to me<" not in html and "Unassigned</span>" in html


def test_payment_cases_show_their_clock(client, app_db):
    cid = sql(app_db, "SELECT id FROM cases WHERE product_kind = 'payment' AND state != 'accepted' ORDER BY deadline LIMIT 1")[0][0]
    html = client.get(f"/queue?owner=all&case={cid}").text
    row = re.search(rf'<tr class="case-row" data-case="{cid}".*?</tr>', html, re.S).group(0)
    assert "15-day clock" in row


def test_summary_state_words():
    from workbench.views.queue import summary_state
    assert summary_state("available", 6, 1) == "6 claims, 1 to check"
    assert summary_state("available", 1, 0) == "1 claim, all checked"
    assert summary_state("none", 0, 0) == "No draft yet" and summary_state("rejected", 0, 0) == "Draft rejected"
