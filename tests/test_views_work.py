"""Departments, Team and Pipeline views."""
import re
import sqlite3

import yaml
from fastapi.testclient import TestClient

from workbench.app import create_app
from tests.test_overview import main_of, text_of

NOTE = "Shares out work. It does not rank people."


def as_role(client, role, sid):
    client.cookies.set("role", role)
    client.cookies.set("staff_id", sid)


def data_rows(html):
    return re.findall(r"<tr[^>]*>\s*<th scope=\"row\"", main_of(html))


def test_handler_sees_own_row_and_average_and_lead_sees_eleven(client):
    html = main_of(client.get("/team").text)  # default identity is the handler H1
    assert len(data_rows(html)) == 2 and "Team average" in html and 'class="avg-row"' in html
    as_role(client, "team_lead", "T1")
    lead = main_of(client.get("/team").text)
    assert len(data_rows(lead)) == 11 and "Team average" not in lead
    assert NOTE in text_of(lead) and "Unassigned" in lead


def test_team_rows_go_by_role_then_name_not_by_numbers(client, app_db):
    as_role(client, "team_lead", "T1")
    names = re.findall(r'<th scope="row">([^<]+)<span class="who">(\w+)</span>', main_of(client.get("/team").text))
    want = sqlite3.connect(app_db).execute("SELECT name, role FROM staff WHERE role IN ('handler','specialist') ORDER BY role != 'handler', name").fetchall()
    assert [(n, r.lower()) for n, r in names] == [(n, r) for n, r in want]


def test_team_returned_by_specialists_shows_count_and_share(client, app_db):
    as_role(client, "team_lead", "T1")
    html = main_of(client.get("/team").text)
    from workbench import stats
    back = stats.returned_by_handler(sqlite3.connect(app_db))
    n, r = back["H1"]
    assert f"{r} of {n}, {r / n:.0%}" in html


def test_unassigned_list_buttons_follow_the_rules(client, app_db):
    html = main_of(client.get("/team").text)  # handler: may assign to themselves
    first = re.search(r'<ol class="att unassigned">.*?/cases/(AB-\d{4}-\d{5})', html, re.S).group(1)
    assert "Assign to me" in html and 'name="next" value="/team"' in html
    want = sqlite3.connect(app_db).execute("SELECT id FROM cases WHERE state != 'accepted' AND owner_id IS NULL ORDER BY deadline, id").fetchone()[0]
    assert first == want
    as_role(client, "specialist", "S1")
    assert "Assign to me" not in main_of(client.get("/team").text)  # the rules layer does not let specialists assign


def test_assign_from_team_goes_back_to_team(client, app_db):
    cid, ver = sqlite3.connect(app_db).execute("SELECT id, version FROM cases WHERE state != 'accepted' AND owner_id IS NULL ORDER BY deadline, id").fetchone()
    r = client.post(f"/cases/{cid}/assign", data={"version": str(ver), "next": "/team"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/team"
    assert sqlite3.connect(app_db).execute("SELECT owner_id FROM cases WHERE id = ?", (cid,)).fetchone()[0] == "H1"


def test_unassigned_load_more_continues_the_list(client, app_db):
    n = sqlite3.connect(app_db).execute("SELECT COUNT(*) FROM cases WHERE state != 'accepted' AND owner_id IS NULL").fetchone()[0]
    first = re.findall(r'/cases/(AB-\d{4}-\d{5})"', main_of(client.get("/team").text).split('class="att unassigned"')[1])
    more = client.get("/team/unassigned?offset=20").text
    rest = re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', more)
    assert len(first) == min(20, n) and not set(first) & set(rest) and len(first) + len(rest) == min(40, n)
    assert ('hx-get="/team/unassigned?offset=40"' in more) == (n > 40)


def test_pipeline_flow_has_coloured_linked_stages_and_hidden_numbers(client, app_db):
    html = main_of(client.get("/pipeline").text)
    db = sqlite3.connect(app_db)
    for s in ("new", "in_review", "handed_over", "returned", "accepted"):
        assert f'class="flow-node st-{s}"' in html and f'href="/queue?owner=all&amp;state={s}"' in html
    n = dict(db.execute("SELECT state, COUNT(*) FROM cases GROUP BY state").fetchall())
    assert f"{n['new']} here now" in html and f"{n['accepted']} closed" in html
    assert '<table class="sr-only">' in html and "Show the numbers" not in html and "<details" not in html
    assert "8 weeks" in html and "15 business days, 35" in html and "By stage" in html
    assert "More charts" not in html and 'class="stage"' not in html


def test_removing_a_path_removes_it_from_the_numbers(app_db, tmp_path):
    cfg = yaml.safe_load(open("config/pipeline.yaml", encoding="utf-8"))
    cfg["paths"] = [p for p in cfg["paths"] if p["kind"] != "returned"]
    alt = tmp_path / "pipeline.yaml"
    alt.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    c = TestClient(create_app(str(app_db), str(alt), models_dir=None), base_url="http://127.0.0.1:8000")
    full = TestClient(create_app(str(app_db), models_dir=None), base_url="http://127.0.0.1:8000")
    row = "<td>Handed over</td><td>Returned</td>"
    assert row in full.get("/pipeline").text
    assert row not in c.get("/pipeline").text


def test_specialist_departments_lists_only_their_handovers(client, app_db):
    c = sqlite3.connect(app_db)  # the plain test data has no departments yet
    c.execute("UPDATE cases SET department = CASE WHEN rowid % 2 THEN 'Fraud claims' ELSE 'Bereavement' END WHERE state = 'handed_over'")
    c.commit()
    as_role(client, "specialist", "S1")
    html = main_of(client.get("/departments?department=Bereavement").text)
    ids = re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', html)
    rows = c.execute("SELECT id FROM cases WHERE state = 'handed_over' AND department = 'Fraud claims' ORDER BY deadline, id").fetchall()
    assert ids == [r[0] for r in rows][:20]
    assert "dept-chips" not in html and "Fraud claims" in html  # no chips: their department is the page
    assert "Accept" in html and re.search(r"\d+ days? (late|left)|Due today", html)
    assert re.search(r'class="tag (warm|ok)"', html)


def test_departments_chips_count_open_cases_and_mark_the_current_one(client, app_db):
    c = sqlite3.connect(app_db)
    c.execute("UPDATE cases SET department = 'Fraud claims' WHERE rowid % 3 = 0")
    c.commit()
    open_, fraud = c.execute("SELECT COUNT(*), SUM(department = 'Fraud claims') FROM cases WHERE state != 'accepted'").fetchone()
    html = main_of(client.get("/departments?department=Fraud+claims").text)
    assert f'>All <b>{open_:,}</b>' in html
    assert re.search(rf'aria-current="page">Fraud claims <b>{fraud}</b>', html)


def test_departments_lead_has_no_buttons_and_filters_narrow(client, app_db):
    c = sqlite3.connect(app_db)
    c.execute("UPDATE cases SET department = 'Fraud claims' WHERE rowid % 2 = 0")
    c.commit()
    as_role(client, "team_lead", "T1")
    html = main_of(client.get("/departments?department=Fraud+claims").text)
    assert "Accept" not in html
    narrow = main_of(client.get("/departments?department=Fraud+claims&source=letter&type=Service").text)
    assert "Channel: Letter" in narrow and "Type: Service" in narrow
    ok = c.execute("SELECT COUNT(*) FROM cases WHERE state != 'accepted' AND department = 'Fraud claims' AND source = 'letter' AND type = 'Service'").fetchone()[0]
    assert re.search(rf'<span class="kpi-label">Open</span>\s*<span class="kpi-value">{ok}</span>', narrow)
    assert "Channel:" not in main_of(client.get("/departments?source=nonsense").text)  # unknown values are ignored


def test_departments_load_more_continues_the_handovers(client, app_db):
    c = sqlite3.connect(app_db)
    c.execute("UPDATE cases SET department = 'Fraud claims', state = 'handed_over' WHERE rowid <= 50")
    c.commit()
    as_role(client, "specialist", "S1")
    html = main_of(client.get("/departments").text)
    first = re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', html)
    assert len(first) == 20 and "Load more (30 left)" in html
    more = client.get("/departments/handovers?department=Bereavement&offset=20").text  # their own department, whatever the link says
    rest = re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', more)
    want = [r[0] for r in c.execute("SELECT id FROM cases WHERE state = 'handed_over' AND department = 'Fraud claims' ORDER BY deadline, id")]
    assert first + rest == want[:40] and "Accept" in more


def test_new_views_write_nothing(client, app_db):
    def snap():
        c = sqlite3.connect(app_db)
        return c.execute("SELECT (SELECT COUNT(*) FROM audit), (SELECT COUNT(*) FROM events), (SELECT COUNT(*) FROM claims), (SELECT SUM(version) FROM cases)").fetchone()
    before = snap()
    for role, sid in (("handler", "H1"), ("specialist", "S1"), ("team_lead", "T1")):
        as_role(client, role, sid)
        for u in ("/departments", "/team", "/pipeline", "/departments/handovers?offset=20", "/team/unassigned?offset=20"):
            assert client.get(u).status_code == 200
    assert snap() == before


def test_accept_is_refused_for_everyone_but_the_departments_specialist(client, app_db):
    c = sqlite3.connect(app_db)
    c.execute("UPDATE cases SET department = 'Fraud claims' WHERE state = 'handed_over'")
    c.commit()
    cid, ver = c.execute("SELECT id, version FROM cases WHERE state = 'handed_over' ORDER BY id").fetchone()
    for role, sid in (("handler", "H1"), ("specialist", "S2"), ("team_lead", "T1")):  # S2 is Financial difficulty
        as_role(client, role, sid)
        r = client.post(f"/cases/{cid}/accept", data={"version": str(ver)})
        assert r.status_code == 403, role
        assert c.execute("SELECT state, version FROM cases WHERE id = ?", (cid,)).fetchone() == ("handed_over", ver)


def test_department_rows_add_up_to_the_open_cases(app_db):
    from workbench import stats
    from workbench.config import load_config
    from datetime import date
    c = sqlite3.connect(app_db)
    c.row_factory = sqlite3.Row
    cfg = load_config()
    rows = stats.department_rows(c, cfg, date(2026, 11, 10))
    open_ = stats.headline(c, date(2026, 11, 10), cfg["bank_holidays"])["open"]
    assert rows[-1]["department"] == "No department yet" and sum(r["open"] for r in rows) == open_


def test_audit_page_names_people_without_seconds(client):
    client.cookies.set("role", "team_lead"); client.cookies.set("staff_id", "T1")  # noqa: E702
    html = client.get("/audit").text
    assert "<td>System</td>" in html and "T1 team_lead" not in html
    import re
    assert not re.search(r"\d\d:\d\d:\d\d", html)  # filter placement is checked in test_views_reference.py


def test_audit_detail_is_plain_words(client):
    import re
    client.cookies.set("role", "team_lead"); client.cookies.set("staff_id", "T1")  # noqa: E702
    html = client.get("/audit").text
    body = html[html.index("<tbody>"):html.index("</tbody>")]
    assert "_" not in re.sub(r'href="[^"]*"|<[^>]*>', "", body) and "from:" not in body and "source:" not in body
    assert "By " in body
