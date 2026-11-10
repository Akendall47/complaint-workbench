"""Web app: shell, role switcher, deadline strip and the Queue. Routes never change a case themselves;
they call workbench.cases and show its NotAllowed and StaleCase messages as plain text."""
import contextlib
import os
import re
import socket
import sys
import threading
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import audit, cases
from .cases import Actor, NotAllowed, StaleCase
from .classify import MODELS_DIR, ensure_models
from .config import load_config
from .db import connect
from .deadlines import add_business_days, business_days_left
from .urgency import urgent_reasons

HERE = Path(__file__).parent
DEMO = {"handler": "H1", "specialist": "S1", "team_lead": "T1"}
ROLE_NAME = {"handler": "Handler", "specialist": "Specialist", "team_lead": "Team lead"}
HOME = {"handler": "/queue", "specialist": "/departments", "team_lead": "/"}
STATE_NAME = {"new": "New", "in_review": "In review", "handed_over": "Handed over", "returned": "Returned", "accepted": "Accepted"}
NAV = [("Overview", "/"), ("Queue", "/queue"), ("Case", None), ("Departments", "/departments"), ("Team", "/team"),
       ("Pipeline", "/pipeline"), ("Policy library", "/policies"), ("Audit log", "/audit"), ("Settings", "/settings")]
LOCAL_HOSTS = {"127.0.0.1", "localhost", "testserver"}
CASE_ID = re.compile(r"^AB-\d{4}-\d{5}$")
PER_PAGE = 50
NOT_FOUND = "Database not found. Run: uv run python -m workbench.generate"


def current_actor(request) -> Actor:
    role, sid = request.cookies.get("role"), request.cookies.get("staff_id")
    if role in DEMO and sid == DEMO[role]:
        return Actor(sid, role)
    return Actor("H1", "handler")


def rise_pairs(conn, cfg) -> list[tuple[str, str]]:
    """Department and type pairs whose count this week is at least ratio x the average of the previous weeks."""
    r, today = cfg["rise"], date.fromisoformat(cfg["today"])
    day = lambda n: str(today - timedelta(days=n))  # noqa: E731
    q = ("SELECT department, type, COUNT(*) FROM cases WHERE department IS NOT NULL AND type IS NOT NULL"
         " AND substr(received_at,1,10) BETWEEN ? AND ? GROUP BY 1,2")
    now = {(d, t): n for d, t, n in conn.execute(q, (day(6), day(0)))}
    w = r["baseline_weeks"]
    before = {(d, t): n for d, t, n in conn.execute(q, (day(7 * w + 6), day(7)))}
    return sorted(k for k, n in now.items() if n >= r["minimum_cases"] and n >= r["ratio"] * before.get(k, 0) / w)


def strip(conn, cfg) -> dict:
    today = date.fromisoformat(cfg["today"])
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    limit = cfg["urgent"]["deadline_within_business_days"]
    edge = str(add_business_days(today, limit + 1, hol) - timedelta(days=1))  # last date still within the limit
    one = lambda q, *a: conn.execute(q, a).fetchone()[0]  # noqa: E731
    open_ = "state != 'accepted' AND "
    rises = rise_pairs(conn, cfg)
    return {"past": one(f"SELECT COUNT(*) FROM cases WHERE {open_}deadline < ?", cfg["today"]),
            "soon": one(f"SELECT COUNT(*) FROM cases WHERE {open_}deadline >= ? AND deadline <= ?", cfg["today"], edge),
            "urgent": one(f"SELECT COUNT(*) FROM cases WHERE {open_}urgent = 1"),
            "rises": len(rises), "rise_query": urlencode({"owner": "all", "department": rises[0][0], "type": rises[0][1]}) if rises else "",
            "limit": limit, "edge": edge, "updated": audit.now()[11:16]}


def create_app(db_path="data/workbench.db", config_path="config/pipeline.yaml", models_dir=MODELS_DIR) -> FastAPI:
    cfg = load_config(config_path)
    content = yaml.safe_load((HERE / "content.yaml").read_text(encoding="utf-8"))
    today = date.fromisoformat(cfg["today"])
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    audit.set_clock(lambda: datetime.fromisoformat(cfg["today"] + "T12:30:00"))  # demo clock: today, 12:30
    if models_dir is not None:  # trains on first start when the model files are missing
        with contextlib.closing(connect(db_path)) as c:
            ensure_models(c, cfg, models_dir)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")  # autoescape on for .html
    templates.env.globals["content"] = content

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method == "POST":
            host, origin = request.headers.get("host", ""), request.headers.get("origin")
            if host.split(":")[0] not in LOCAL_HOSTS or (origin and urlparse(origin).netloc != host):
                return PlainTextResponse("Request refused: it did not come from this app.", status_code=403)
        resp = await call_next(request)
        resp.headers["Content-Security-Policy"] = "default-src 'self'"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    @contextlib.contextmanager
    def db():
        c = connect(db_path)
        try:
            yield c
        finally:
            c.close()

    def page(request, conn, name, status=200, **ctx):
        actor = current_actor(request)
        last = request.cookies.get("last_case", "")
        nav = [{"label": label, "href": href or (f"/cases/{last}" if CASE_ID.match(last) else None),
                "sub": last if href is None and CASE_ID.match(last) else "",
                "current": request.url.path.startswith("/cases/") if href is None else request.url.path == href,
                "home": href == HOME[actor.role]} for label, href in NAV]
        return templates.TemplateResponse(request, name, {"actor": actor, "role_name": ROLE_NAME, "roles": DEMO, "nav": nav,
                                                          "strip": strip(conn, cfg), "cfg": cfg, **ctx}, status_code=status)

    def queue_ctx(conn, actor, q: dict) -> dict:
        one = lambda k: (q.get(k) or [""])[0] if isinstance(q.get(k), list) else (q.get(k) or "")  # noqa: E731
        owner = one("owner")
        if owner not in ("me", "unassigned", "all"):
            owner = "me" if actor.role == "handler" else "all"
        due = one("due") if one("due") in ("past", "soon") else ""
        urgent = one("urgent") == "1"
        state = one("state") or one("stage")
        f = {"owner": owner, "department": one("department"), "type": one("type"), "state": state, "urgent": "1" if urgent else "",
             "due": due}
        where, args = [], []
        if state:
            where.append("c.state = ?"); args.append(state)  # noqa: E702
        else:
            where.append("c.state != 'accepted'")
        for col in ("department", "type"):
            if f[col]:
                where.append(f"c.{col} = ?"); args.append(f[col])  # noqa: E702
        if owner == "me":
            where.append("c.owner_id = ?"); args.append(actor.id)  # noqa: E702
        elif owner == "unassigned":
            where.append("c.owner_id IS NULL")
        if urgent:
            where.append("c.urgent = 1")
        if due:
            s = strip(conn, cfg)
            where.append("c.state != 'accepted'")
            if due == "past":
                where.append("c.deadline < ?"); args.append(cfg["today"])  # noqa: E702
            else:
                where.append("c.deadline >= ? AND c.deadline <= ?"); args += [cfg["today"], s["edge"]]  # noqa: E702
        w = " AND ".join(where)
        total = conn.execute(f"SELECT COUNT(*) FROM cases c WHERE {w}", args).fetchone()[0]
        pages = max(1, -(-total // PER_PAGE))
        try:
            pg = min(max(1, int(one("page"))), pages)
        except ValueError:
            pg = 1
        got = conn.execute(f"SELECT c.* FROM cases c WHERE {w} ORDER BY c.deadline, c.urgent DESC, c.id LIMIT ? OFFSET ?",
                           (*args, PER_PAGE, (pg - 1) * PER_PAGE)).fetchall()
        expand = one("expand")
        rows = [{"c": r, "days": business_days_left(date.fromisoformat(r["deadline"]), today, hol), "open": r["id"] == expand}
                for r in got]
        detail = None
        for row in rows:
            if row["open"]:
                c = row["c"]
                notes = " ".join(n[0] for n in conn.execute("SELECT body FROM notes WHERE case_id = ?", (c["id"],)))
                detail = row["detail"] = {"reasons": urgent_reasons(c, notes, today, cfg),
                                          "next": cases.next_action(conn, c["id"], actor.role)}
        keep = {k: v for k, v in f.items() if v}
        link = lambda **kw: "/queue?" + urlencode({**keep, **{k: v for k, v in kw.items() if v}})  # noqa: E731
        sel = {"departments": list(cfg["departments"]), "types": cfg["types"], "states": list(STATE_NAME)}
        return {"rows": rows, "f": f, "page_no": pg, "pages": pages, "link": link, "state_name": STATE_NAME,
                "filtered": bool(keep.keys() - {"owner"}), "here": link(page=str(pg) if pg > 1 else "", expand=one("expand")),
                "sel": sel, "detail": detail}

    @app.get("/queue", response_class=HTMLResponse)
    def queue(request: Request):
        with db() as conn:
            return page(request, conn, "queue.html", **queue_ctx(conn, current_actor(request), parse_qs(request.url.query)))

    def back_to(nxt: str) -> str:
        return nxt if nxt.startswith("/queue") and not nxt.startswith("//") else "/queue"

    @app.post("/cases/{case_id}/assign")
    def assign(request: Request, case_id: str, version: str = Form(""), next: str = Form("/queue")):
        actor, nxt = current_actor(request), back_to(next)
        try:
            with db() as conn:
                try:
                    cases.assign(conn, case_id, actor, int(version), actor.id)
                except ValueError:
                    raise NotAllowed("That form was not valid. Reload the page.")
                return RedirectResponse(nxt, status_code=303)
        except (NotAllowed, StaleCase) as e:
            with db() as conn:
                q = parse_qs(urlparse(nxt).query)
                return page(request, conn, "queue.html", status=409 if isinstance(e, StaleCase) else 403,
                            message=str(e), **queue_ctx(conn, actor, q))

    @app.post("/role")
    def role(request: Request, role: str = Form("")):
        if role not in DEMO:
            return PlainTextResponse("Choose handler, specialist or team lead.", status_code=400)
        if request.headers.get("HX-Request"):
            resp = HTMLResponse(templates.get_template("partials/role_notice.html").render(), headers={"HX-Refresh": "true"})
        else:  # no script: go back to the same page
            ref = urlparse(request.headers.get("referer", ""))
            same = ref.netloc == request.headers.get("host") and ref.path.startswith("/") and not ref.path.startswith("//")
            resp = RedirectResponse((ref.path + ("?" + ref.query if ref.query else "")) if same else "/queue", status_code=303)
        resp.set_cookie("role", role, httponly=True, samesite="lax")
        resp.set_cookie("staff_id", DEMO[role], httponly=True, samesite="lax")
        return resp

    return app


def main() -> None:
    import uvicorn
    db_path = os.environ.get("WORKBENCH_DB", "data/workbench.db")
    port = int(os.environ.get("WORKBENCH_PORT", "8000"))
    if not Path(db_path).exists():
        print(NOT_FOUND, file=sys.stderr)
        sys.exit(1)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            print(f"Port {port} is in use. Close the other copy of the workbench, then run again.", file=sys.stderr)
            sys.exit(1)
    app = create_app(db_path)
    threading.Timer(1.5, webbrowser.open, [f"http://127.0.0.1:{port}/"]).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
