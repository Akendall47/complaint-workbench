"""Web app: the shell (security headers, page frame, role switch, deadline pills) and app start. Page routes live in views/;
they never change a case themselves:
they call workbench.cases and show its NotAllowed and StaleCase messages as plain text."""
import contextlib
import os
import re
import socket
import sys
import threading
import webbrowser
from types import SimpleNamespace
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import audit, drafts, stats
from .classify import MODELS_DIR, ensure_models
from .config import load_config
from .db import connect
from .deadlines import due_soon_edge
from .views.shared import DEMO, HOME, ROLE_NAME, STATE_NAME, current_actor, strip, to_int  # noqa: F401  (tests import them from here)

HERE = Path(__file__).parent
NAV = [("Overview", "/"), ("Queue", "/queue"), ("Case", None), ("Departments", "/departments"), ("Team", "/team"),
       ("Pipeline", "/pipeline"), ("Policy library", "/policies"), ("Audit log", "/audit"), ("Settings", "/settings")]
MINOR = {"/policies", "/audit", "/settings"}  # reference pages: quieter links at the end of the nav
# The hosts this app answers to: this machine, plus a hosted name (WORKBENCH_HOSTS, or the one Render sets) when deployed.
LOCAL_HOSTS = {"127.0.0.1", "localhost", *filter(None, [*os.environ.get("WORKBENCH_HOSTS", "").split(","), os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")])}
KNOWN_PATHS = {p for _, p in NAV if p}
CASE_ID = re.compile(r"^AB-\d{4}-\d{5}\Z")  # \Z: a trailing newline does not match
PER_PAGE = 50
NOT_FOUND = "Database not found. Run: uv run python -m workbench.generate"


def safe_path(url: str) -> str | None:
    """The url if it is a path on this app (a known route or a case page), else None. Used for every redirect back."""
    u = urlparse(url)
    if u.scheme or u.netloc or not url.startswith("/") or url.startswith("//"):
        return None
    ok = u.path in KNOWN_PATHS or (u.path.startswith("/cases/") and CASE_ID.match(u.path.removeprefix("/cases/")))
    return url if ok else None


def create_app(db_path="data/workbench.db", config_path="config/pipeline.yaml", models_dir=MODELS_DIR) -> FastAPI:
    cfg = load_config(config_path)
    content = yaml.safe_load((HERE / "content.yaml").read_text(encoding="utf-8"))
    today = date.fromisoformat(cfg["today"])
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    audit.set_clock(lambda: datetime.fromisoformat(cfg["today"] + "T12:30:00"))  # demo clock: today, 12:30
    if models_dir is not None:  # trains on first start when the model files are missing
        with contextlib.closing(connect(db_path)) as c:
            ensure_models(c, cfg, models_dir)
    with contextlib.closing(connect(db_path)) as c:  # recordings become claim rows once, here; no page load writes
        for (cid,) in c.execute("SELECT id FROM cases WHERE department IS NOT NULL").fetchall():
            if drafts.rec_path(cfg, cid).exists():
                drafts.store_claims(c, cid, cfg)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")  # autoescape on for .html
    templates.env.globals["content"] = content

    def secure(resp):
        resp.headers["Content-Security-Policy"] = "default-src 'self'"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    def from_this_app(request) -> bool:
        """Cross-site request guard: the request must come from this same origin (scheme, host and port)."""
        host = request.headers.get("host", "")
        if urlparse("//" + host).hostname not in LOCAL_HOSTS:
            return False
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site":
            return False
        if origin is not None:
            o = urlparse(origin)
            return o.scheme == request.url.scheme and o.netloc == host
        if request.headers.get("sec-fetch-site") in ("same-origin", "none"):
            return True
        ref = request.headers.get("referer")
        r = urlparse(ref or "")
        return bool(ref) and r.netloc == host and r.scheme == request.url.scheme

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if urlparse("//" + request.headers.get("host", "")).hostname not in LOCAL_HOSTS:
            return secure(PlainTextResponse("Request refused: unknown host.", status_code=403))
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
        last = ctx.get("case_now") or request.cookies.get("last_case", "")
        if not CASE_ID.match(last):  # nothing opened yet: Case opens the case that needs this person first
            first = stats.needs_attention(conn, actor, limit=1)
            last = first[0]["id"] if first else ""
        nav = [{"label": label, "href": href or (f"/cases/{last}" if CASE_ID.match(last) else None),
                "sub": last if href is None and CASE_ID.match(last) else "",
                "current": request.url.path.startswith("/cases/") if href is None else request.url.path == href,
                "home": href == HOME[actor.role], "minor": href in MINOR} for label, href in NAV]
        return templates.TemplateResponse(request, name, {"actor": actor, "role_name": ROLE_NAME, "roles": DEMO, "nav": nav,
                                                          "strip": ctx.pop("strip", None) or strip(conn, cfg, edge_of(request)), "cfg": cfg,
                                                          "alerts_on": request.cookies.get("alerts") != "off", **ctx}, status_code=status)

    from .views import case, overview, queue, reference, work  # one module per page area; each adds its own routes
    x = SimpleNamespace(cfg=cfg, today=today, hol=hol, db=db, page=page, edge_of=edge_of, templates=templates, models_dir=models_dir)
    overview.register(app, x)
    queue.register(app, x)

    work.register(app, x)

    reference.register(app, x)

    case.register(app, x)



    @app.post("/prefs/alerts")
    def alerts(request: Request, show: str = Form("")):
        """Show or hide the deadline pills at the top of each page: a viewer preference kept in a cookie, like the demo role."""
        if request.headers.get("HX-Request"):
            resp = HTMLResponse("", headers={"HX-Refresh": "true"})
        else:  # no script: go back to the same page
            ref = urlparse(request.headers.get("referer", ""))
            same = ref.netloc == request.headers.get("host") and ref.scheme == request.url.scheme
            resp = RedirectResponse((same and safe_path(ref.path + ("?" + ref.query if ref.query else ""))) or "/", status_code=303)
        resp.set_cookie("alerts", "on" if show == "1" else "off", httponly=True, samesite="lax")
        return resp



    @app.post("/role")
    def role(request: Request, role: str = Form("")):
        if role not in DEMO:
            return PlainTextResponse("Choose handler, specialist or team lead.", status_code=400)
        if request.headers.get("HX-Request"):
            resp = HTMLResponse(templates.get_template("partials/role_notice.html").render(), headers={"HX-Refresh": "true"})
        else:  # no script: go back to the same page
            ref = urlparse(request.headers.get("referer", ""))
            same = ref.netloc == request.headers.get("host") and ref.scheme == request.url.scheme
            resp = RedirectResponse((same and safe_path(ref.path + ("?" + ref.query if ref.query else ""))) or "/queue", status_code=303)
        resp.set_cookie("role", role, httponly=True, samesite="lax")
        resp.set_cookie("staff_id", DEMO[role], httponly=True, samesite="lax")
        return resp

    return app


def main() -> None:
    import uvicorn
    db_path = os.environ.get("WORKBENCH_DB", "data/workbench.db")
    port = int(os.environ.get("PORT") or os.environ.get("WORKBENCH_PORT", "8000"))
    bind = os.environ.get("WORKBENCH_BIND", "127.0.0.1")
    if not Path(db_path).exists():
        print(NOT_FOUND, file=sys.stderr)
        sys.exit(1)
    if bind == "127.0.0.1":  # on this machine: check the port and open the browser
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                print(f"Port {port} is in use. Close the other copy of the workbench, then run again.", file=sys.stderr)
                sys.exit(1)
        threading.Timer(1.5, webbrowser.open, [f"http://127.0.0.1:{port}/"]).start()
    app = create_app(db_path)
    # Hosted behind an HTTPS proxy: trust its forwarded scheme, so the same-origin check compares https with https.
    uvicorn.run(app, host=bind, port=port, log_level="warning", proxy_headers=bind != "127.0.0.1", forwarded_allow_ips="*" if bind != "127.0.0.1" else None)
