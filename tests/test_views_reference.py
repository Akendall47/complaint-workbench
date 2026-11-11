"""Policy library, Audit log and Settings."""
import re
import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.test_overview import main_of, text_of
from workbench import audit
from workbench.app import create_app
from workbench.classify import _save
from workbench.search import highlight

HDR = {"Origin": "http://127.0.0.1:8000"}
CLAUSE = r'<li id="POL-[\d.]+"'


def as_role(client, role, sid):
    client.cookies.set("role", role)
    client.cookies.set("staff_id", sid)


@pytest.fixture
def writer(app_db, built, tmp_path):
    """A client whose app has trained models, so POST /intake can route a complaint."""
    _save({k: built[k]["model"] for k in ("department", "type")}, tmp_path / "models")
    return TestClient(create_app(str(app_db), models_dir=tmp_path / "models"), base_url="http://127.0.0.1:8000", headers=HDR)


def test_search_for_a_clause_id_returns_it_first_and_every_clause_has_an_anchor(client):
    html = main_of(client.get("/policies?q=POL-4.2").text)
    assert re.findall(r'<li id="(POL-[\d.]+)"', html)[0] == "POL-4.2"
    everything = main_of(client.get("/policies").text)
    assert len(re.findall(CLAUSE, everything)) == 40 and everything.count('<span class="count">') == 9  # all clauses, then 8 sections


def test_a_section_filters_the_clauses_and_keeps_the_search(client):
    html = main_of(client.get("/policies?section=Bereavement").text)
    assert len(re.findall(CLAUSE, html)) == 5 and 'aria-current="true">Bereavement' in html
    assert len(re.findall(CLAUSE, main_of(client.get("/policies?section=No+such+section").text))) == 40  # unknown section: ignored
    found = main_of(client.get("/policies?q=death&section=Bereavement").text)
    assert "<mark>" in found and 'aria-current="true">Bereavement' in found
    assert 'href="/policies?q=death&amp;section=Bereavement"' in main_of(client.get("/policies?q=death").text)  # a section link keeps the search


def test_highlight_escapes_before_it_marks():
    out = highlight("<img src=x onerror=alert(1)> & card", "card img")
    assert "<img" not in out and "&lt;" in out and "<mark>card</mark>" in out and "<mark>img</mark>" in out
    assert "&amp;" in out


def test_policy_search_odd_input_is_safe(client):
    for q in ('"', "NEAR AND", "'; DROP TABLE policies; --", "<script>alert(1)</script>", "x" * 5000):
        r = client.get("/policies", params={"q": q})
        assert r.status_code == 200 and "<script>alert" not in r.text


def test_audit_newest_first_with_verified_chip_for_team_lead(writer, app_db):
    as_role(writer, "team_lead", "T1")
    for t in ("My card payment was taken twice, please refund it.", "I want to complain about my branch queue."):
        writer.post("/intake", data={"text": t, "source": "phone"})
    html = main_of(writer.get("/audit").text)
    n = sqlite3.connect(app_db).execute("SELECT COUNT(*) FROM audit").fetchone()[0]
    assert f"Chain verified, {n:,} entries" in text_of(html)
    ids = re.findall(r'href="/cases/(AB-\d{4}-\d{5})"', html)
    assert ids[0] > ids[1]  # the second complaint came last, so it is listed first
    assert html.index('class="filters"') < html.index("<table")  # the filters are a row above the table


def test_audit_is_for_the_team_lead_only(client):
    for role, sid in (("handler", "H1"), ("specialist", "S1")):
        as_role(client, role, sid)
        r = client.get("/audit")
        html = main_of(r.text)
        assert r.status_code == 200 and "The audit log is for the team lead." in html and 'name="role" value="team_lead"' in html
        assert "<table" not in html and "Chain" not in html
        assert client.get("/audit/rows").status_code == 403  # the Load older route is closed too


def test_audit_filters_validate_and_paging_clamps(client, app_db):
    as_role(client, "team_lead", "T1")
    c = sqlite3.connect(app_db)
    c.row_factory = sqlite3.Row
    for i in range(120):
        audit.append(c, actor_id="H1", role="handler", action="open", case_id="AB-2026-00001", detail={"reason": f"r{i}"})
    c.commit()
    ok = main_of(client.get("/audit?case=AB-2026-00001&actor=H1").text)
    assert ok.count("<tr><td") == 50 and "Load older (70 left)" in text_of(ok) and "/audit/rows?" in ok  # one page, then a button for the rest
    assert "Newer" not in ok
    more = client.get("/audit/rows?case=AB-2026-00001&actor=H1&page=2").text
    assert more.count("<tr><td") == 50 and "Load older (20 left)" in text_of(more)
    for q in ("case=%27%3B+DROP+TABLE+audit%3B--", "case=AB-2026-00001%0A", "actor=nobody", "actor=%3Cb%3E"):
        r = client.get("/audit?" + q)
        assert r.status_code == 200 and "No entries match" in r.text, q
    for q in ("page=abc", "page=-4", "page=0", "page=99999"):
        assert client.get("/audit?" + q).status_code == 200
    last = main_of(client.get("/audit?actor=H1&case=AB-2026-00001&page=99999").text)  # the no-script fallback clamps to the last page
    assert last.count("<tr><td") == 20 and "Load older" not in last and "Newer" in last
    assert c.execute("SELECT COUNT(*) FROM audit").fetchone()[0] >= 120  # reading changed nothing


def test_audit_reason_text_is_escaped(client, app_db):
    as_role(client, "team_lead", "T1")
    c = sqlite3.connect(app_db)
    c.row_factory = sqlite3.Row
    audit.append(c, actor_id="H1", role="handler", action="return", detail={"reason": "<script>alert(1)</script>"})
    c.commit()
    html = client.get("/audit").text
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)" in html


def test_settings_lists_the_public_sources_the_assumptions_rules_and_model(client):
    html = client.get("/settings").text
    assert 'id="data-sources"' in html
    main = main_of(html)
    assert "Every complaint, customer and member of staff here is synthetic." in main and "No real customer data is used." in main
    assert len(re.findall(r"<tr><td>", main)) == 7  # one row per verified public source
    for want in ("1.85 million", "54.8% upheld", "857,757 of 1,740,909", "18,900 of 32,900", "£576.4m", "£85,000", "23 Feb 2021", "22 Oct 2026"):
        assert want in main, want
    links = re.findall(r'<a href="(https://[^"]+)" target="_blank" rel="noopener noreferrer"', main)
    assert len(links) == 7 and "https://www.fca.org.uk/consumers/how-complain" in links and not any("handbook.fca.org.uk" in u for u in links)
    assert "Our assumptions (no public source)" in main and "34% of handovers" in main and "Channel mix" in main
    for word in ("Routing threshold", "Deadlines", "Unusual rise", "Urgent", "qwen3:4b-instruct", "no network call"):
        assert word in main


def test_empty_test_complaint_shows_the_message_and_adds_nothing(writer, app_db):
    before = sqlite3.connect(app_db).execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    r = writer.post("/intake", data={"text": "  ", "source": "phone"})
    assert "Enter the complaint text." in r.text and r.status_code == 400
    assert sqlite3.connect(app_db).execute("SELECT COUNT(*) FROM cases").fetchone()[0] == before


def test_bad_text_is_kept_next_to_the_message(writer):
    r = writer.post("/intake", data={"text": "x" * 5001, "source": "phone"})
    assert "too long" in r.text
    r = writer.post("/intake", data={"text": "Some words I typed", "source": "carrier pigeon"})
    assert "Choose where the complaint came from." in r.text and "Some words I typed</textarea>" in r.text
    assert 'maxlength="5000"' in r.text


def test_test_complaint_with_markup_is_created_audited_and_shown_escaped(writer, app_db):
    as_role(writer, "team_lead", "T1")
    r = writer.post("/intake", data={"text": "<img src=x onerror=alert(1)> my card was stolen", "source": "email"})
    cid = re.search(r'href="/cases/(AB-\d{4}-\d{5})"', r.text).group(1)
    row = sqlite3.connect(app_db).execute("SELECT actor_id, role FROM audit WHERE case_id = ? AND action = 'received'", (cid,)).fetchone()
    assert row == ("T1", "team_lead")
    case = writer.get(f"/cases/{cid}?all=1").text
    assert "<img src=x" not in case and "&lt;img src=x" in case


def test_intake_post_goes_through_the_request_guard(writer):
    r = writer.post("/intake", data={"text": "hello there", "source": "phone"}, headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
    assert writer.get("/intake").status_code == 405  # no GET writes
