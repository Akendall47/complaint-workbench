"""Departments, Team and Pipeline views."""
import re
import sqlite3

import yaml
from fastapi.testclient import TestClient

from workbench.app import create_app
from tests.test_overview import main_of, text_of

NOTE = "This page is for sharing out work. It does not show speed per case, because a speed target pushes people to approve AI drafts without checking."


def as_role(client, role, sid):
    client.cookies.set("role", role)
    client.cookies.set("staff_id", sid)


def data_rows(html):
    return re.findall(r"<tr[^>]*>\s*<th scope=\"row\"", main_of(html))


def test_handler_sees_one_team_row_and_lead_sees_eleven(client):
    html = client.get("/team").text  # default identity is the handler H1
    assert len(data_rows(html)) == 1 and "Switch to Team lead (bottom left) to see the whole team." in text_of(main_of(html))
    as_role(client, "team_lead", "T1")
    lead = client.get("/team").text
    assert len(data_rows(lead)) == 11 and "Unassigned" in lead
    assert "rank" not in text_of(main_of(lead)).lower()
    assert NOTE in text_of(main_of(lead))


def test_team_rows_sorted_by_past_deadline(client):
    as_role(client, "team_lead", "T1")
    html = main_of(client.get("/team").text)
    past = [int(n) for n in re.findall(r'<td class="num-col(?: deadline-past)?">(\d+)</td><td class="num-col">\d+</td><td class="num-col">\d+</td>', html)]
    assert past == sorted(past, reverse=True) and len(past) == 11


def test_pipeline_boxes_count_open_cases_link_to_queue_and_say_returns(client, app_db):
    html = main_of(client.get("/pipeline").text)
    db = sqlite3.connect(app_db)
    open_ = db.execute("SELECT COUNT(*) FROM cases WHERE state != 'accepted'").fetchone()[0]
    boxes = re.findall(r'<a class="stage" href="/queue\?owner=all&amp;stage=(\w+)"><span>([^<]+)</span><b>(\d+)</b>', html)
    assert [b[1] for b in boxes] == ["New", "In review", "Handed over", "Returned"]
    assert sum(int(b[2]) for b in boxes) == open_
    back, ho = db.execute("SELECT SUM(return_count > 0), COUNT(*) FROM cases WHERE handed_over_at IS NOT NULL").fetchone()
    assert f"{back} of {ho} handovers were returned for more work." in text_of(html)
    assert "band" not in html and "Stage</th>" not in html  # no flow diagram, no second stage table


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


def test_departments_waiting_list_is_capped_with_plain_deadline_words(client, app_db):
    c = sqlite3.connect(app_db)  # the plain test data has no departments yet
    c.execute("UPDATE cases SET department = 'Fraud claims' WHERE state = 'handed_over'")
    c.commit()
    as_role(client, "specialist", "S1")
    html = main_of(client.get("/departments").text)
    assert html.count('class="plain-id"') <= 8
    assert re.search(r"\d+ business days? (past deadline|left)|Due today", html)


def test_specialist_departments_lists_only_their_handovers(client, app_db):
    c = sqlite3.connect(app_db)  # the plain test data has no departments yet
    c.execute("UPDATE cases SET department = CASE WHEN rowid % 2 THEN 'Fraud claims' ELSE 'Bereavement' END WHERE state = 'handed_over'")
    c.commit()
    as_role(client, "specialist", "S1")
    html = main_of(client.get("/departments?department=Bereavement").text)
    ids = re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', html)
    rows = sqlite3.connect(app_db).execute("SELECT id FROM cases WHERE state = 'handed_over' AND department = 'Fraud claims' ORDER BY deadline, id").fetchall()
    assert ids == [r[0] for r in rows][:8]
    assert "Waiting for Fraud claims" in html and "Bereavement" not in html
    assert "Accept" in html and "Past deadline" in html
    assert html.index("Past deadline") < html.index("Open</th>")  # first number column


def test_departments_lead_has_no_buttons_and_filters_narrow(client, app_db):
    as_role(client, "team_lead", "T1")
    html = main_of(client.get("/departments?department=Fraud+claims").text)
    assert "Accept" not in html.replace("Specialists accept", "")
    narrow = main_of(client.get("/departments?department=Fraud+claims&source=letter&type=Service").text)
    assert "Source: letter" in narrow and "Type: Service" in narrow
    ok = sqlite3.connect(app_db).execute("SELECT COUNT(*) FROM cases WHERE state != 'accepted' AND department = 'Fraud claims' AND source = 'letter' AND type = 'Service'").fetchone()[0]
    assert f'<td class="num-col">{ok}</td>' in narrow
    assert "Source:" not in main_of(client.get("/departments?source=nonsense").text)  # unknown values are ignored


def test_new_views_write_nothing(client, app_db):
    def snap():
        c = sqlite3.connect(app_db)
        return c.execute("SELECT (SELECT COUNT(*) FROM audit), (SELECT COUNT(*) FROM events), (SELECT COUNT(*) FROM claims), (SELECT SUM(version) FROM cases)").fetchone()
    before = snap()
    for role, sid in (("handler", "H1"), ("specialist", "S1"), ("team_lead", "T1")):
        as_role(client, role, sid)
        for u in ("/departments", "/team", "/pipeline"):
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


def test_department_rows_add_up_to_the_open_cases(client, app_db):
    from workbench import stats
    from workbench.config import load_config
    from datetime import date
    c = sqlite3.connect(app_db)
    c.row_factory = sqlite3.Row
    cfg = load_config()
    rows = stats.department_rows(c, cfg, date(2026, 11, 10))
    open_ = c.execute("SELECT COUNT(*) FROM cases WHERE state != 'accepted'").fetchone()[0]
    assert rows[-1]["department"] == "No department yet" and sum(r["open"] for r in rows) == open_
    assert "No department yet" in main_of(client.get("/departments").text)
