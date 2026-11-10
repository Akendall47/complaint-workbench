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
    r = TestClient(create_app(str(app_db), models_dir=None)).get("/queue?department=Bereavement&urgent=1&due=past")
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


def test_unassigned_rows_offer_assign(client):
    html = client.get("/queue?owner=unassigned").text
    assert rows(html) and html.count(">Assign to me<") == len(rows(html))
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


def test_no_details_row_and_no_urgent_chip(client):
    first = rows(client.get("/queue?owner=all").text)[0][0]
    html = client.get(f"/queue?owner=all&expand={first}").text
    assert "detail-row" not in html and ">Details<" not in html and 'class="urgent-tag"' not in html


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
