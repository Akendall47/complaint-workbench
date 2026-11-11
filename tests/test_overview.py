import re
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from workbench import stats
from workbench.app import create_app
from workbench.cases import Actor
from workbench.config import load_config
from workbench.db import connect, init_db


def main_of(html):
    body = re.search(r'<main.*?</main>', html, re.S).group(0)
    return re.sub(r'<div id="help".*?</div>', "", body, flags=re.S)  # the closed help panel is not page content


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_overview_figures_and_no_strip_repeating_them(client):
    html = client.get("/").text
    body = main_of(html)
    for label in ("Past deadline", "Due in 5 business days", "Urgent", "Open complaints", "Typical days open", "Handovers returned"):
        assert label in body
    assert body.count('class="kpi"') == 6
    assert 'class="strip"' not in html  # the figures card already shows these counts


def test_change_chips_name_the_date_and_never_rely_on_colour(client):
    body = main_of(client.get("/").text)
    chips = re.findall(r'<span class="change (better|worse|same)"[^>]*>([^<]+)</span>', body)
    assert chips and all(t.endswith("vs 3 Nov") and (t.startswith(("up ", "down ", "no change"))) for _, t in chips)


def test_needs_attention_lists_ten_cases_matching_the_stats_then_load_more(client, app_db):
    body = main_of(client.get("/").text)
    got = re.findall(r'<a href="/cases/(AB-\d{4}-\d{5})" class="plain-id"', body)
    c = connect(app_db)
    actor = Actor("H1", "handler")
    assert got == [r["id"] for r in stats.needs_attention(c, actor, limit=10)]
    n = stats.attention_count(c, actor)
    if n > 10:
        assert 'hx-get="/overview/attention?offset=10"' in body
        more = client.get("/overview/attention?offset=10").text
        assert re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', more) == [r["id"] for r in stats.needs_attention(c, actor, limit=10, offset=10)]


@pytest.mark.parametrize("role, sid", [("specialist", "S1"), ("team_lead", "T1")])
def test_overview_for_other_roles(client, role, sid):
    client.cookies.set("role", role)
    client.cookies.set("staff_id", sid)
    assert client.get("/").status_code == 200


def test_every_chart_has_a_text_alternative_and_no_inline_style_or_script(client):
    body = main_of(client.get("/").text)
    labels = re.findall(r'<figure class="[^"]+" role="img" aria-label="([^"]+)"', body)
    assert len(labels) >= 3 and all(labels)
    assert body.count('<table class="sr-only">') >= 3  # the numbers, for screen readers
    assert "<script" not in body and "style=" not in body


def test_daily_chart_numbers_match_the_stats(client, app_db):
    body = main_of(client.get("/").text)
    fig = re.search(r'<figure class="area-chart".*?</figure>', body, re.S).group(0)
    got = [int(v) for v in re.findall(r"<tr><td>[^<]*</td><td>(\d+)</td></tr>", fig)]
    with connect(app_db) as c:
        assert got == [n for _, n in stats.daily(c, date(2026, 11, 10))]


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
    with connect(app_db) as c2:
        r = stats.rises(c2, date(2026, 11, 10), load_config())[0]
    assert f"{r['this_week']} this week, usual {r['usual']:.0f}" in text_of(body)
    assert 'href="/queue?owner=all&amp;department=Bereavement&amp;type=Service"' in body


def test_data_sources_link_in_the_footer_and_no_intro_text(client):
    body = main_of(client.get("/").text)
    assert 'href="/settings#data-sources"' in client.get("/").text  # in the footer of every page
    for gone in ("New here?", "Where these numbers come from"):
        assert gone not in body


def test_figures_show_typical_days_in_plain_words(client, app_db):
    body = text_of(main_of(client.get("/").text))
    with connect(app_db) as c:
        h = stats.headline(c, date(2026, 11, 10), {date.fromisoformat(d) for d in load_config()["bank_holidays"]})
    assert f"Open complaints {h['open']:,}" in body.replace(" up", "").replace(" down", "")
    assert f"Typical days open {int(h['avg_days_open'] + .5)}" in body
    assert f"Handovers returned {h['returned_share']:.0%}" in body
    assert "median" not in body.lower()  # said in the help panel only


def test_zero_cases_returns_200(tmp_path):
    db = tmp_path / "empty.db"
    c = connect(db)
    init_db(c)
    c.close()
    cl = TestClient(create_app(str(db), models_dir=None), base_url="http://127.0.0.1:8000")
    r = cl.get("/")
    assert r.status_code == 200 and "Open complaints" in r.text
