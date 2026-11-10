import re
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from workbench.app import create_app, current_actor, main
from workbench.config import load_config
from workbench.deadlines import business_days_left

NAV = ["/", "/queue", "/departments", "/team", "/pipeline", "/policies", "/audit", "/settings"]
BUILT = {"/queue"}


@pytest.mark.parametrize("path", [pytest.param(p, marks=[] if p in BUILT else pytest.mark.xfail(reason="view not built yet", strict=True))
                                  for p in NAV])
def test_navigation_link_returns_200(client, path):
    assert client.get(path).status_code == 200


def test_navigation_order_and_skip_link_first(client):
    html = client.get("/queue").text
    assert html.index('class="skip"') < html.index("<nav")
    labels = re.findall(r'<a class="nav-link"[^>]*>\s*([^<]+?)\s*<', html)
    assert labels[:2] == ["Overview", "Queue"]
    assert labels[-6:] == ["Departments", "Team", "Pipeline", "Policy library", "Audit log", "Settings"]


def test_deadline_strip_counts_equal_direct_counts(client, app_db):
    cfg = load_config()
    today = date.fromisoformat(cfg["today"])
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    c = sqlite3.connect(app_db)
    open_ = c.execute("SELECT deadline, urgent FROM cases WHERE state != 'accepted'").fetchall()
    past = sum(d < cfg["today"] for d, _ in open_)
    soon = sum(d >= cfg["today"] and business_days_left(date.fromisoformat(d), today, hol) <= 5 for d, _ in open_)
    urgent = sum(u == 1 for _, u in open_)
    html = client.get("/queue").text
    strip = re.sub(r"\s+", " ", re.search(r'<ul class="strip".*?</ul>', html, re.S).group(0))
    assert f"Past deadline <b>{past}</b>" in strip
    assert f"Due within 5 business days <b>{soon}</b>" in strip
    assert f"Urgent <b>{urgent}</b>" in strip
    assert "Updated 12:30" in strip
    assert "Rises" not in strip  # none in a 200-case set


def test_strip_shows_rise_when_one_exists(app_db):
    c = sqlite3.connect(app_db)
    for i in range(12):
        c.execute("INSERT INTO cases(id, received_at, state, department, type, deadline, urgent, version, product_kind)"
                  " VALUES (?, '2026-11-09T10:00:00', 'new', 'Bereavement', 'Service', '2027-01-01', 0, 0, 'other')", (f"X{i}",))
    c.commit()
    html = TestClient(create_app(str(app_db), models_dir=None), base_url="http://127.0.0.1:8000").get("/queue").text
    assert re.search(r"Rises <b>1</b>", html)
    assert "department=Bereavement" in html


def test_unknown_role_cookie_is_handler(client):
    for cookies in ({"role": "admin"}, {"role": "team_lead", "staff_id": "H1"}, {}):
        client.cookies.clear()
        for k, v in cookies.items():
            client.cookies.set(k, v)
        r = client.get("/queue")
        assert r.status_code == 200
        assert re.search(r'aria-pressed="true"[^>]*>\s*Handler', r.text)


def test_current_actor():
    class R:
        def __init__(self, c):
            self.cookies = c
    assert current_actor(R({"role": "specialist", "staff_id": "S1"})) == ("S1", "specialist")
    assert current_actor(R({"role": "team_lead", "staff_id": "T1"})) == ("T1", "team_lead")
    assert current_actor(R({"role": "admin", "staff_id": "T1"})) == ("H1", "handler")
    assert current_actor(R({})) == ("H1", "handler")


def test_post_role_stays_on_page(client):
    r = client.post("/role", data={"role": "team_lead"}, headers={"HX-Request": "true", "Referer": "http://127.0.0.1:8000/queue?due=past"})
    assert r.status_code == 200 and r.headers["HX-Refresh"] == "true"
    assert "Demo only" in r.text
    assert client.cookies.get("role") == "team_lead" and client.cookies.get("staff_id") == "T1"
    r = client.post("/role", data={"role": "specialist"}, headers={"Referer": "http://127.0.0.1:8000/queue?due=past"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/queue?due=past"
    r = client.post("/role", data={"role": "specialist"}, headers={"Referer": "http://evil.example/steal"}, follow_redirects=False)
    assert r.headers["location"] == "/queue"
    assert client.post("/role", data={"role": "admin"}).status_code == 400
    r = client.post("/role", data={"role": "specialist"}, headers={"Referer": "http://127.0.0.1:8000/nonsense"}, follow_redirects=False)
    assert r.headers["location"] == "/queue"


def test_post_from_another_site_is_refused(client):
    r = client.post("/role", data={"role": "team_lead"}, headers={"Origin": "http://evil.example"})
    assert r.status_code == 403
    assert client.cookies.get("role") is None


def test_headers(client):
    h = client.get("/queue").headers
    assert h["content-security-policy"] == "default-src 'self'"
    assert h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "same-origin"


def test_no_external_urls_no_inline_script(client):
    html = client.get("/queue").text
    assert not re.search(r'(?:src|href)\s*=\s*["\']https?://', html)
    assert not re.search(r"<script(?![^>]*\bsrc=)", html) and not re.search(r"\son\w+\s*=", html)
    assert "Not an Ankura product" in html
    assert client.get("/static/htmx.min.js").status_code == 200


def test_main_exits_when_database_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1
    assert "Database not found. Run: uv run python -m workbench.generate" in capsys.readouterr().err


def test_main_exits_when_port_in_use(app_db, monkeypatch, capsys):
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    monkeypatch.setenv("WORKBENCH_PORT", str(s.getsockname()[1]))
    monkeypatch.setenv("WORKBENCH_DB", str(app_db))
    with pytest.raises(SystemExit) as e:
        main()
    s.close()
    assert e.value.code == 1
    assert "in use" in capsys.readouterr().err


def _app(app_db):
    return create_app(str(app_db), models_dir=None)


def test_security_headers_on_every_response(app_db):
    app = _app(app_db)
    app.add_api_route("/boom", lambda: 1 / 0)
    c = TestClient(app, base_url="http://127.0.0.1:8000", raise_server_exceptions=False)
    for r in (c.post("/role", data={"role": "team_lead"}),  # 403 from the guard
              c.get("/nope"), c.delete("/queue"), c.get("/boom"), c.get("/static/app.css"),
              c.post("/role", headers={"Origin": "http://127.0.0.1:8000"})):  # 422 validation
        assert r.headers["content-security-policy"] == "default-src 'self'", r.status_code
        assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "same-origin"
    boom = c.get("/boom")
    assert boom.status_code == 500 and boom.text == "Something went wrong" and "Traceback" not in boom.text


def test_post_guard_origin_rules(app_db):
    c = TestClient(_app(app_db), base_url="http://127.0.0.1:8000")
    go = lambda **h: c.post("/role", data={"role": "team_lead"}, headers=h).status_code  # noqa: E731
    assert go() == 403  # no Origin, no Referer
    assert go(Origin="http://127.0.0.1:9999") == 403
    assert go(Origin="https://127.0.0.1:8000") == 403
    assert go(Origin="null") == 403
    assert go(**{"Sec-Fetch-Site": "cross-site"}) == 403
    assert go(Referer="http://127.0.0.1:9999/queue") == 403
    assert go(Origin="http://127.0.0.1:8000", **{"HX-Request": "true"}) == 200
    assert go(**{"Sec-Fetch-Site": "same-origin", "HX-Request": "true"}) == 200
    assert go(Referer="http://127.0.0.1:8000/queue", **{"HX-Request": "true"}) == 200


def test_unknown_host_refused(app_db):
    c = TestClient(_app(app_db), base_url="http://testserver")
    assert c.post("/role", data={"role": "team_lead"}, headers={"Origin": "http://testserver"}).status_code == 403


def test_htmx_eval_off_tabs_and_pager(client):
    html = client.get("/queue?owner=all").text
    assert '"allowEval": false' in html
    assert re.search(r'class="segmented".*?aria-current="page"', html, re.S)
    assert '<nav class="pager" aria-label="Pages"' in html


def test_host_checked_on_every_request(app_db):
    c = TestClient(_app(app_db), base_url="http://127.0.0.1:8000")
    r = c.get("/queue", headers={"Host": "evil.example"})
    assert r.status_code == 403 and r.headers["content-security-policy"] == "default-src 'self'"
    assert c.get("/queue").status_code == 200


def test_guard_cross_site_fetch_and_referer_scheme(app_db):
    c = TestClient(_app(app_db), base_url="http://127.0.0.1:8000")
    go = lambda **h: c.post("/role", data={"role": "team_lead"}, headers=h).status_code  # noqa: E731
    assert go(Referer="http://127.0.0.1:8000/queue", **{"Sec-Fetch-Site": "cross-site"}) == 403
    assert go(Referer="https://127.0.0.1:8000/queue") == 403


def test_role_switch_without_script_uses_same_origin_referer(client):
    r = client.post("/role", data={"role": "specialist"}, headers={"Referer": "http://127.0.0.1:8000/cases/AB-2026-00001"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/cases/AB-2026-00001"


def test_safe_return_path(client, app_db):
    from workbench.app import safe_path
    assert safe_path("/queue?owner=all") == "/queue?owner=all" and safe_path("/cases/AB-2026-00001") == "/cases/AB-2026-00001"
    for bad in ("/queuefoo", "//evil", r"/\evil", "http://evil.example", "/nonsense"):
        assert safe_path(bad) is None, bad
    r = client.post("/cases/AB-2026-00001/assign", data={"version": 0, "next": "/queuefoo"})
    assert "/queuefoo" not in r.text
