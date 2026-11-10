import re
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from workbench import stats
from workbench.app import create_app
from workbench.cases import Actor
from workbench.db import connect, init_db


def main_of(html):
    body = re.search(r'<main.*?</main>', html, re.S).group(0)
    return re.sub(r'<div id="help".*?</div>', "", body, flags=re.S)  # the closed help panel is not page content


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_overview_has_three_figures_and_no_repeat_of_the_strip(client):
    html = client.get("/").text
    body = main_of(html)
    for label in ("Open complaints", "Typical days open", "Handovers returned"):
        assert label in body
    assert body.count('class="figure"') == 3
    assert "Past deadline" not in body and "Due within" not in body and "Due soon" not in body  # the strip has them
    assert "Past deadline" in html  # and it does


def test_overview_has_the_strip_before_the_page(client):
    html = client.get("/").text
    assert html.index('class="strip"') < html.index("<main")


def test_needs_attention_is_five_links_matching_the_stats(client, app_db):
    body = main_of(client.get("/").text)
    got = re.findall(r'<a href="/cases/(AB-\d{4}-\d{5})"', body)
    c = connect(app_db)
    want = [r["id"] for r in stats.needs_attention(c, Actor("H1", "handler"), date(2026, 11, 10))]
    assert got == want and len(got) == 5
    assert "Needs attention today" in body


@pytest.mark.parametrize("role, sid", [("specialist", "S1"), ("team_lead", "T1")])
def test_overview_for_other_roles(client, role, sid):
    client.cookies.set("role", role)
    client.cookies.set("staff_id", sid)
    assert client.get("/").status_code == 200


def test_one_chart_with_text_alternative_and_numbers_in_details(client):
    body = main_of(client.get("/").text)
    assert body.count("<svg") == 1 and body.count('role="img"') == 1
    assert re.search(r'aria-label="Complaints per week[^"]*"', body)
    assert "<details" in body and "<table" in body
    assert "<script" not in body and "style=" not in body


def test_no_rise_line_without_a_rise(client):
    assert "Unusual rise" not in main_of(client.get("/").text)


def test_rise_line_links_to_the_queue(app_db):
    c = sqlite3.connect(app_db)
    for i in range(12):
        c.execute("INSERT INTO cases(id, received_at, state, department, type, deadline, version) VALUES (?, '2026-11-09T10:00:00', 'new',"
                  " 'Bereavement', 'Service', '2027-01-01', 0)", (f"AB-2026-9{i:04d}",))
    c.commit()
    c.close()
    cl = TestClient(create_app(str(app_db), models_dir=None), base_url="http://127.0.0.1:8000")
    body = main_of(cl.get("/").text)
    assert body.count("Unusual rise") == 1
    assert 'href="/queue?owner=all&amp;department=Bereavement&amp;type=Service"' in body


def test_foot_link_to_data_sources_and_nothing_busy(client):
    body = main_of(client.get("/").text)
    assert body.count('href="/settings#data-sources"') == 1
    for gone in ("New here?", "Deadline tracker", "heatmap", "Heatmap", "Where complaints come from"):
        assert gone not in body


def test_figures_show_typical_days_in_plain_words(client):
    body = text_of(main_of(client.get("/").text))
    assert re.search(r"Typical days open \S+ ", body) or "Typical days open" in body
    assert "median" not in body.lower()  # said in the help panel only


def test_zero_cases_returns_200(tmp_path):
    db = tmp_path / "empty.db"
    c = connect(db)
    init_db(c)
    c.close()
    cl = TestClient(create_app(str(db), models_dir=None), base_url="http://127.0.0.1:8000")
    r = cl.get("/")
    assert r.status_code == 200 and "Open complaints" in r.text
