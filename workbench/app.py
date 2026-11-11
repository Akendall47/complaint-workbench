"""Web app: shell, role switcher, deadline strip and the Queue. Routes never change a case themselves;
they call workbench.cases and show its NotAllowed and StaleCase messages as plain text."""
import contextlib
import json
import os
import re
import socket
import sys
import threading
import webbrowser
from types import SimpleNamespace
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import yaml
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import audit, case_view, cases, charts, drafts, stats
from .cases import NotAllowed, StaleCase
from .classify import MODELS_DIR, ensure_models
from .intake import MAX_TEXT, IntakeError, receive
from .search import highlight, search_policies
from .config import load_config
from .db import connect
from .deadlines import business_days_left, due_soon_edge
from .views.shared import DEMO, HOME, ROLE_NAME, STATE_NAME, current_actor, strip, to_int  # noqa: F401  (tests import them from here)

HERE = Path(__file__).parent
NAV = [("Overview", "/"), ("Queue", "/queue"), ("Case", None), ("Departments", "/departments"), ("Team", "/team"),
       ("Pipeline", "/pipeline"), ("Policy library", "/policies"), ("Audit log", "/audit"), ("Settings", "/settings")]
MINOR = {"/policies", "/audit", "/settings"}  # reference pages: quieter links at the end of the nav
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
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


def _plain(r) -> str:
    """The Detail column in plain words: the reason if there is one, how a complaint came in, else nothing."""
    try:
        d = json.loads(r["detail_json"] or "{}")
    except ValueError:
        return ""
    if not isinstance(d, dict):
        return ""
    if d.get("reason"):
        return str(d["reason"])
    return f'By {d["source"]}' if r["action"] == "received" and d.get("source") else ""


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
        nav = [{"label": label, "href": href or (f"/cases/{last}" if CASE_ID.match(last) else None),
                "sub": last if href is None and CASE_ID.match(last) else "",
                "current": request.url.path.startswith("/cases/") if href is None else request.url.path == href,
                "home": href == HOME[actor.role], "minor": href in MINOR} for label, href in NAV]
        return templates.TemplateResponse(request, name, {"actor": actor, "role_name": ROLE_NAME, "roles": DEMO, "nav": nav,
                                                          "strip": ctx.pop("strip", None) or strip(conn, cfg, edge_of(request)), "cfg": cfg,
                                                          "alerts_on": request.cookies.get("alerts") != "off", **ctx}, status_code=status)

    from .views import case, overview, queue, reference, work  # one module per page area; each adds its own routes
    x = SimpleNamespace(cfg=cfg, today=today, hol=hol, db=db, page=page, edge_of=edge_of, templates=templates)
    overview.register(app, x)
    queue.register(app, x)

    work.register(app, x)

    reference.register(app, x)

    case.register(app, x)


    # ==== QUEUE (moves to views/queue.py) ====

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
        got = conn.execute(f"SELECT c.*, s.name AS owner_name FROM cases c LEFT JOIN staff s ON s.id = c.owner_id WHERE {w} ORDER BY c.deadline, c.urgent DESC, c.id LIMIT ? OFFSET ?",
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

    # ==== SHELL (stays here) ====

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

    # ==== WORK (moves to views/work.py) ====

    # ---- Departments, Team, Pipeline ----
    @app.get("/departments", response_class=HTMLResponse)
    def departments(request: Request):
        actor, q = current_actor(request), request.query_params
        source = q.get("source") if q.get("source") in cfg["sources"] else ""
        type_ = q.get("type") if q.get("type") in cfg["types"] else ""
        with db() as conn:
            row = conn.execute("SELECT department FROM staff WHERE id = ? AND role = 'specialist'", (actor.id,)).fetchone() if actor.role == "specialist" else None
            mine = row[0] if row else None  # a specialist's ?department= is ignored: they see their own department only
            rows = stats.department_rows(conn, cfg, today, source, type_)
            if mine:  # a specialist sees their own department only
                rows = [r for r in rows if r["department"] == mine]
            chosen = mine or (q.get("department") if q.get("department") in cfg["departments"] else rows[0]["department"])
            waiting, n_waiting = stats.handovers(conn, chosen, source, type_, limit=8)
            for c in waiting:
                c["can"] = cases.can_decide(conn, c["id"], actor)[0]  # the rules layer decides who gets the buttons
            missing = stats.missing_by_field(conn, cfg, chosen, source, type_)[:6]
            title = f"Fields most often missing, {chosen}"
            keep = {k: v for k, v in (("source", source), ("type", type_)) if v}
            return page(request, conn, "departments.html", rows=rows, chosen=chosen, waiting=waiting, n_waiting=n_waiting, can_act=any(c["can"] for c in waiting),
                        days=lambda d: business_days_left(date.fromisoformat(d), today, hol), source=source, type_=type_,
                        link=lambda d: "/departments?" + urlencode({"department": d, **keep}),
                        clear=lambda k: "/departments?" + urlencode({"department": chosen, **{a: b for a, b in keep.items() if a != k}}),
                        queue_link="/queue?" + urlencode({"owner": "all", "state": "handed_over", "department": chosen}),
                        chart=charts.bars(missing, title=title, summary=stats.sentence("bars", {"title": title, "items": missing}) if missing else ""))

    @app.get("/team", response_class=HTMLResponse)
    def team(request: Request):
        actor = current_actor(request)
        with db() as conn:
            everyone = stats.team(conn, today)
            lead = actor.role == "team_lead"
            rows = everyone if lead else [r for r in everyone if r["id"] == actor.id]
            return page(request, conn, "team.html", rows=rows, lead=lead, unassigned=stats.unassigned(conn))

    @app.get("/pipeline", response_class=HTMLResponse)
    def pipeline(request: Request):
        kind = {"normal": "Normal path", "urgent": "Urgent fast path", "returned": "Returned for more work", "second_return": "Returned a second time"}
        nm = lambda n: STATE_NAME.get(n, n.capitalize())  # noqa: E731
        with db() as conn:
            states = dict(stats.by_stage(conn))
            stages = [(s, states.get(s, 0)) for s in cfg["stages"] if s != "accepted"]  # accepted is closed, so not an open count
            moves = [(nm(p["from"]), nm(p["to"]), kind.get(p["kind"], p["kind"]), p["count"]) for p in stats.pipeline_paths(conn, cfg)]
            back, ho = stats.handover_returns(conn)
            dept_title = "Open complaints by department"
            by_dept = [(r["department"], r["open"]) for r in stats.by_department(conn)]
            more = [(dept_title, charts.bars(by_dept, title=dept_title, summary=stats.sentence("bars", {"title": dept_title, "items": by_dept}) if by_dept else "")),
                    ("When complaints arrive", charts.heatmap(stats.heatmap(conn), title="Complaints received by weekday and hour", summary="Darker cells are busier hours."))]
            return page(request, conn, "pipeline.html", stages=stages, stage_name=STATE_NAME, moves=moves, back=back, handovers=ho, more=more)

    # ==== REFERENCE (moves to views/reference.py) ====

    # ---- Policy library, Audit log, Settings ----
    @app.get("/policies", response_class=HTMLResponse)
    def policies(request: Request):
        q = request.query_params.get("q", "").strip()[:200]
        with db() as conn:
            found = search_policies(conn, q, k=100 if not q else 20)
            groups: dict = {}
            for r in found:
                groups.setdefault("Best matches" if q else r["section"], []).append({"id": r["id"], "section": r["section"], "title": r["title"], "snippet": highlight(r["snippet"] + ("" if q else "…"), q)})  # the empty-query snippet is cut at 160 characters
            return page(request, conn, "policies.html", q=q, groups=groups, n=len(found))

    def audit_ctx(conn, q) -> dict:
        case, actor = q.get("case", ""), q.get("actor", "")
        people = [r[0] for r in conn.execute("SELECT id FROM staff ORDER BY id")] + ["system"]  # intake writes as "system"
        where, args = [], []
        bad = (case and not CASE_ID.match(case)) or (actor and actor not in people)
        if case:
            where.append("case_id = ?"); args.append(case)  # noqa: E702
        if actor:
            where.append("actor_id = ?"); args.append(actor)  # noqa: E702
        w = (" WHERE " + " AND ".join(where)) if where else ""
        total = 0 if bad else conn.execute(f"SELECT COUNT(*) FROM audit{w}", args).fetchone()[0]
        pages = max(1, -(-total // PER_PAGE))
        pg = to_int(q.get("page"), 1)
        pg = min(max(1, pg), pages)
        got = [] if bad else conn.execute(f"SELECT audit.*, (SELECT name FROM staff WHERE staff.id = audit.actor_id) AS who FROM audit{w} ORDER BY id DESC LIMIT ? OFFSET ?", (*args, PER_PAGE, (pg - 1) * PER_PAGE)).fetchall()
        broken = audit.verify_chain(conn)
        everything = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        keep = {k: v for k, v in (("case", case), ("actor", actor)) if v}
        return {"rows": [{**dict(r), "what": _plain(r), "when": r["at"][:16].replace("T", " "),
                          "by": "System" if r["actor_id"] == "system" else f'{r["who"] or r["actor_id"]}, {r["role"].replace("_", " ").capitalize()}'} for r in got], "people": people, "case": case, "actor": actor,
                "page_no": pg, "pages": pages, "chain": "Chain verified: " + f"{everything:,} entries" if broken is None else f"Chain broken at entry {broken}",
                "chain_ok": broken is None, "link": lambda p: "/audit?" + urlencode({**keep, "page": p})}

    @app.get("/audit", response_class=HTMLResponse)
    def audit_log(request: Request):
        allowed = current_actor(request).role == "team_lead"  # a notice, not a 403 page, for everyone else
        with db() as conn:
            return page(request, conn, "audit.html", allowed=allowed, **(audit_ctx(conn, request.query_params) if allowed else {}))

    def settings_page(request, status=200, **ctx):
        with db() as conn:
            return page(request, conn, "settings.html", status=status, **{"max_text": MAX_TEXT, "text": "", "source": "", **ctx})

    @app.get("/settings", response_class=HTMLResponse)
    def settings(request: Request):
        return settings_page(request)

    @app.post("/intake", response_class=HTMLResponse)
    def intake(request: Request, text: str = Form(""), source: str = Form("")):
        actor = current_actor(request)
        try:
            with db() as conn:
                models = ensure_models(conn, cfg, models_dir if models_dir is not None else MODELS_DIR)
                cid = receive(conn, text=text, source=source, cfg=cfg, models=models, actor_id=actor.id, role=actor.role)
        except IntakeError as e:
            return settings_page(request, status=400, error=str(e), text=text, source=source)
        return settings_page(request, added=cid)

    # ==== QUEUE assign (moves to views/queue.py) ====

    def back_to(nxt: str) -> str:
        return safe_path(nxt) or "/queue"

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


    # ==== CASE (moves to views/case.py) ====

    # ---- Case view ----
    def gone(request):
        """The case does not exist. A swap target gets a small fragment, a page the not-found page."""
        if request.headers.get("HX-Request"):
            return HTMLResponse('<div id="case" tabindex="-1" hx-history="false"><p class="notice" role="alert">Case not found</p></div>', status_code=404)
        with db() as conn:
            return page(request, conn, "not_found.html", status=404)

    def case_response(request, case_id, step=1, all_=False, message=None, status=200, unmasked=False):
        if not CASE_ID.match(case_id):
            return gone(request)
        actor = current_actor(request)
        with db() as conn:
            v = case_view.build(conn, cfg, case_id, actor, step, all_, unmasked)
            if v is None:
                return gone(request)
            ctx = {"v": v, "state_name": STATE_NAME, "message": message, "stale": status == 409, "case_now": case_id}
            if request.headers.get("HX-Request"):
                resp = templates.TemplateResponse(request, "partials/case_main.html", {"actor": actor, "cfg": cfg, **ctx}, status_code=status)
            else:
                resp = page(request, conn, "case.html", status=status, **ctx)
        if unmasked:
            resp.headers["Cache-Control"] = "no-store"  # unmasked text is never kept in a cache
        resp.set_cookie("last_case", case_id, samesite="lax")
        return resp

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def case_page(request: Request, case_id: str, step: str = "1", all: str = "0"):
        return case_response(request, case_id, to_int(step, 1), all == "1")

    def act(request, case_id, version, step, all_, do, unmask=False):
        """Run one cases.py action. Success: htmx gets the fresh fragment, others a redirect. Failure: the plain message."""
        actor, st, al = current_actor(request), to_int(step, 1), all_ == "1"
        if not CASE_ID.match(case_id):
            return case_response(request, case_id)
        try:
            ver = to_int(version, -1)
            if ver < 0:
                raise NotAllowed("That form was not valid. Reload the page.")
            with db() as conn:
                do(conn, actor, ver)
        except (NotAllowed, StaleCase) as e:
            return case_response(request, case_id, st, al, str(e), 409 if isinstance(e, StaleCase) else 403)
        if unmask:
            return case_response(request, case_id, st, al, unmasked=True)
        if request.headers.get("HX-Request"):
            return case_response(request, case_id, st, al)
        return RedirectResponse(f"/cases/{case_id}?step={st}&all={1 if al else 0}", status_code=303)

    def need_reason(reason):
        if not (reason or "").strip():
            raise NotAllowed("Enter a reason")
        return reason

    def simple(name, fn_name):
        @app.post("/cases/{case_id}/" + name)
        def _(request: Request, case_id: str, version: str = Form(""), step: str = Form("1"), all: str = Form("0")):
            return act(request, case_id, version, step, all, lambda c, a, v: getattr(cases, fn_name)(c, case_id, a, v))
    for n, f in (("open", "open_case"), ("approve", "approve"), ("accept", "accept")):
        simple(n, f)

    def with_reason(name, fn_name):
        @app.post("/cases/{case_id}/" + name)
        def _(request: Request, case_id: str, version: str = Form(""), step: str = Form("1"), all: str = Form("0"), reason: str = Form("")):
            def do(c, a, v):
                getattr(cases, fn_name)(c, case_id, a, v, need_reason(reason))
            return act(request, case_id, version, step, all, do, unmask=name == "unmask")
    for n, f in (("reject", "reject_draft"), ("return", "return_case"), ("unmask", "unmask")):
        with_reason(n, f)

    @app.post("/cases/{case_id}/urgent")
    def set_urgent(request: Request, case_id: str, version: str = Form(""), step: str = Form("1"), all: str = Form("0"),
                   urgent: str = Form(""), reason: str = Form("")):
        return act(request, case_id, version, step, all, lambda c, a, v: cases.set_urgent(c, case_id, a, v, urgent == "1", need_reason(reason)))

    @app.post("/cases/{case_id}/department")
    def set_department(request: Request, case_id: str, version: str = Form(""), step: str = Form("1"), all: str = Form("0"),
                       department: str = Form("")):
        def do(c, a, v):
            cases.set_department(c, case_id, a, v, department)
            drafts.store_claims(c, case_id, cfg)  # the recording loads now, not at the next start; a no-op without one
        return act(request, case_id, version, step, all, do)

    @app.post("/cases/{case_id}/claims")
    def add_claim(request: Request, case_id: str, version: str = Form(""), step: str = Form("1"), all: str = Form("0"), text: str = Form("")):
        return act(request, case_id, version, step, all, lambda c, a, v: cases.add_claim(c, case_id, a, v, text))

    @app.post("/cases/{case_id}/claims/{claim_id}/{what}")
    def claim_action(request: Request, case_id: str, claim_id: int, what: str, version: str = Form(""), step: str = Form("1"),
                     all: str = Form("0"), text: str = Form("")):
        if what not in ("confirm", "edit", "remove"):
            return PlainTextResponse("Not found", status_code=404)
        fn = {"confirm": lambda c, a, v: cases.confirm_claim(c, case_id, a, v, claim_id),
              "edit": lambda c, a, v: cases.edit_claim(c, case_id, a, v, claim_id, text),
              "remove": lambda c, a, v: cases.remove_claim(c, case_id, a, v, claim_id)}[what]
        return act(request, case_id, version, step, all, fn)

    @app.post("/cases/{case_id}/handover")
    async def handover(request: Request, case_id: str):
        if not CASE_ID.match(case_id):
            return gone(request)
        form = await request.form()
        with db() as conn:
            row = conn.execute("SELECT department FROM cases WHERE id = ?", (case_id,)).fetchone()
        names = cfg["departments"].get(row[0] if row else None, {}).get("required_fields", [])
        fields = {n: str(form[f"f_{n}"]) for n in names if f"f_{n}" in form}
        return act(request, case_id, str(form.get("version", "")), str(form.get("step", "2")), str(form.get("all", "0")),
                   lambda c, a, v: cases.set_handover(c, case_id, a, v, fields))

    # ==== SHELL (stays here) ====

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
