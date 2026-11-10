"""Web app: shell, role switcher, deadline strip and the Queue. Routes never change a case themselves;
they call workbench.cases and show its NotAllowed and StaleCase messages as plain text."""
import contextlib
import os
import re
import socket
import sys
import threading
import webbrowser
from datetime import date, datetime
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
from .deadlines import business_days_left, due_soon_edge
from .stats import rise_pairs

HERE = Path(__file__).parent
DEMO = {"handler": "H1", "specialist": "S1", "team_lead": "T1"}
ROLE_NAME = {"handler": "Handler", "specialist": "Specialist", "team_lead": "Team lead"}
HOME = {"handler": "/queue", "specialist": "/departments", "team_lead": "/"}
STATE_NAME = {"new": "New", "in_review": "In review", "handed_over": "Handed over", "returned": "Returned", "accepted": "Accepted"}
NAV = [("Overview", "/"), ("Queue", "/queue"), ("Case", None), ("Departments", "/departments"), ("Team", "/team"),
       ("Pipeline", "/pipeline"), ("Policy library", "/policies"), ("Audit log", "/audit"), ("Settings", "/settings")]
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
KNOWN_PATHS = {p for _, p in NAV if p}
CASE_ID = re.compile(r"^AB-\d{4}-\d{5}$")
PER_PAGE = 50
NOT_FOUND = "Database not found. Run: uv run python -m workbench.generate"


def current_actor(request) -> Actor:
    role, sid = request.cookies.get("role"), request.cookies.get("staff_id")
    if role in DEMO and sid == DEMO[role]:
        return Actor(sid, role)
    return Actor("H1", "handler")


def strip(conn, cfg, edge: str) -> dict:
    limit = cfg["urgent"]["deadline_within_business_days"]
    one = lambda q, *a: conn.execute(q, a).fetchone()[0]  # noqa: E731
    open_ = "state != 'accepted' AND "
    rises = rise_pairs(conn, cfg)
    return {"past": one(f"SELECT COUNT(*) FROM cases WHERE {open_}deadline < ?", cfg["today"]),
            "soon": one(f"SELECT COUNT(*) FROM cases WHERE {open_}deadline >= ? AND deadline <= ?", cfg["today"], edge),
            "urgent": one(f"SELECT COUNT(*) FROM cases WHERE {open_}urgent = 1"),
            "rises": len(rises), "rise_query": urlencode({"owner": "all", "department": rises[0][0], "type": rises[0][1]}) if rises else "",
            "limit": limit, "updated": audit.now()[11:16]}


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

    def secure(resp):
        resp.headers["Content-Security-Policy"] = "default-src 'self'"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        return resp

    def from_this_app(request) -> bool:
        """Cross-site request guard: the request must come from this same origin (scheme, host and port)."""
        host = request.headers.get("host", "")
        if urlparse("//" + host).hostname not in LOCAL_HOSTS:
            return False
        origin = request.headers.get("origin")
        if origin is not None:
            o = urlparse(origin)
            return o.scheme == request.url.scheme and o.netloc == host
        if request.headers.get("sec-fetch-site") in ("same-origin", "none"):
            return True
        ref = request.headers.get("referer")
        return bool(ref) and urlparse(ref).netloc == host

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method == "POST" and not from_this_app(request):
            return secure(PlainTextResponse("Request refused: it did not come from this app.", status_code=403))
        return secure(await call_next(request))

    @app.exception_handler(Exception)
    async def failed(request: Request, exc: Exception):  # the outer error layer skips the middleware above
        return secure(PlainTextResponse("Something went wrong", status_code=500))

    def edge_of(request) -> str:  # once per request, used by the strip and the due filter
        if not hasattr(request.state, "edge"):
            request.state.edge = str(due_soon_edge(today, cfg["urgent"]["deadline_within_business_days"], hol))
        return request.state.edge

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
                                                          "strip": strip(conn, cfg, edge_of(request)), "cfg": cfg, **ctx}, status_code=status)

    def queue_ctx(conn, actor, q: dict, edge: str) -> dict:
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
            where.append("c.state != 'accepted'")
            if due == "past":
                where.append("c.deadline < ?"); args.append(cfg["today"])  # noqa: E702
            else:
                where.append("c.deadline >= ? AND c.deadline <= ?"); args += [cfg["today"], edge]  # noqa: E702
        w = " AND ".join(where)
        total = conn.execute(f"SELECT COUNT(*) FROM cases c WHERE {w}", args).fetchone()[0]
        pages = max(1, -(-total // PER_PAGE))
        try:
            pg = min(max(1, int(one("page"))), pages)
        except ValueError:
            pg = 1
        got = conn.execute(f"SELECT c.* FROM cases c WHERE {w} ORDER BY c.deadline, c.urgent DESC, c.id LIMIT ? OFFSET ?",
                           (*args, PER_PAGE, (pg - 1) * PER_PAGE)).fetchall()
        rows = [{"c": r, "days": business_days_left(date.fromisoformat(r["deadline"]), today, hol)} for r in got]
        keep = {k: v for k, v in f.items() if v}
        link = lambda **kw: "/queue?" + urlencode({**keep, **{k: v for k, v in kw.items() if v}})  # noqa: E731
        sel = {"departments": list(cfg["departments"]), "types": cfg["types"], "states": list(STATE_NAME)}
        return {"rows": rows, "f": f, "page_no": pg, "pages": pages, "link": link, "state_name": STATE_NAME,
                "filtered": bool(keep.keys() - {"owner"}), "here": link(page=str(pg) if pg > 1 else ""), "sel": sel}

    @app.get("/queue", response_class=HTMLResponse)
    def queue(request: Request):
        with db() as conn:
            return page(request, conn, "queue.html", **queue_ctx(conn, current_actor(request), parse_qs(request.url.query), edge_of(request)))

    def back_to(nxt: str) -> str:
        return nxt if nxt.startswith("/queue") and not nxt.startswith("//") else "/queue"

    @app.post("/cases/{case_id}/assign")
    def assign(request: Request, case_id: str, version: str = Form(""), next: str = Form("/queue")):
        actor, nxt = current_actor(request), back_to(next)
        try:
            try:
                ver = int(version)
            except ValueError:
                raise NotAllowed("That form was not valid. Reload the page.")
            with db() as conn:
                cases.assign(conn, case_id, actor, ver, actor.id)
                return RedirectResponse(nxt, status_code=303)
        except (NotAllowed, StaleCase) as e:
            with db() as conn:
                q = parse_qs(urlparse(nxt).query)
                return page(request, conn, "queue.html", status=409 if isinstance(e, StaleCase) else 403,
                            message=str(e), **queue_ctx(conn, actor, q, edge_of(request)))

    @app.post("/role")
    def role(request: Request, role: str = Form("")):
        if role not in DEMO:
            return PlainTextResponse("Choose handler, specialist or team lead.", status_code=400)
        if request.headers.get("HX-Request"):
            resp = HTMLResponse(templates.get_template("partials/role_notice.html").render(), headers={"HX-Refresh": "true"})
        else:  # no script: go back to the same page
            ref = urlparse(request.headers.get("referer", ""))
            same = ref.netloc == request.headers.get("host") and (ref.path in KNOWN_PATHS or CASE_ID.match(ref.path.removeprefix("/cases/")))
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
