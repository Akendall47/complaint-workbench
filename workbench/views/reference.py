"""Policy library, Audit log and Settings, with the test intake form."""
import json
import re
from collections import Counter
from urllib.parse import urlencode

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from .. import audit
from ..classify import MODELS_DIR, ensure_models
from ..intake import MAX_TEXT, IntakeError, receive
from ..search import highlight, search_policies
from .shared import current_actor, to_int

CASE_ID = re.compile(r"^AB-\d{4}-\d{5}\Z")  # \Z: a trailing newline does not match. Own copy, so this module does not need app.py
PER_PAGE = 50


def plain(r) -> str:
    """The audit Detail column in plain words: the reason if there is one, how a complaint came in, else nothing."""
    try:
        d = json.loads(r["detail_json"] or "{}")
    except ValueError:
        return ""
    if not isinstance(d, dict):
        return ""
    if d.get("reason"):
        return str(d["reason"])
    return f'By {d["source"]}' if r["action"] == "received" and d.get("source") else ""


def audit_rows(conn, q) -> dict:
    """One page of audit entries, newest first, for the filters in `q`. A bad filter shows no rows, it never reaches the SQL."""
    case, actor = q.get("case", ""), q.get("actor", "")
    people = [r[0] for r in conn.execute("SELECT id FROM staff ORDER BY id")] + ["system"]  # intake writes as "system"
    bad = (case and not CASE_ID.match(case)) or (actor and actor not in people)
    where, args = [], []
    for col, v in (("case_id", case), ("actor_id", actor)):
        if v:
            where.append(f"{col} = ?")
            args.append(v)
    w = (" WHERE " + " AND ".join(where)) if where else ""
    total = 0 if bad else conn.execute(f"SELECT COUNT(*) FROM audit{w}", args).fetchone()[0]
    pages = max(1, -(-total // PER_PAGE))
    pg = min(max(1, to_int(q.get("page"), 1)), pages)
    got = [] if bad else conn.execute(
        f"SELECT audit.*, (SELECT name FROM staff WHERE staff.id = audit.actor_id) AS who FROM audit{w} ORDER BY id DESC LIMIT ? OFFSET ?",
        (*args, PER_PAGE, (pg - 1) * PER_PAGE)).fetchall()
    keep = {k: v for k, v in (("case", case), ("actor", actor)) if v}
    rows = [{**dict(r), "what": plain(r), "when": r["at"][:16].replace("T", " "),
             "by": "System" if r["actor_id"] == "system" else f'{r["who"] or r["actor_id"]}, {r["role"].replace("_", " ").capitalize()}'} for r in got]
    return {"rows": rows, "people": people, "case": case, "actor": actor, "total": total, "page_no": pg, "pages": pages,
            "left": max(0, total - pg * PER_PAGE),
            "link": lambda p: "/audit?" + urlencode({**keep, "page": p}),  # the no-script fallback
            "more": lambda p: "/audit/rows?" + urlencode({**keep, "page": p})}


def register(app, x):
    """Add the Policy library, Audit log, Settings and intake routes. `x` carries cfg, db, page, templates and models_dir."""
    cfg, db, page, templates = x.cfg, x.db, x.page, x.templates

    @app.get("/policies", response_class=HTMLResponse)
    def policies(request: Request):
        q = request.query_params.get("q", "").strip()[:200]
        with db() as conn:
            every = search_policies(conn, q, k=100 if not q else 20)  # empty query: every clause, in order
            counts = Counter(r["section"] for r in every)
            sec = request.query_params.get("section", "")
            sec = sec if sec in counts else ""
            found = search_policies(conn, q, k=100 if not q else 20, sections=[sec]) if sec else every
            body = {} if q else dict(conn.execute("SELECT id, body FROM policies").fetchall())  # no search: the whole clause, not a cut snippet
            groups: dict = {}
            for r in found:
                name = "" if q or sec else r["section"]  # headings only when the list is the whole library
                groups.setdefault(name, []).append({"id": r["id"], "section": r["section"], "title": r["title"],
                                                    "snippet": highlight(body.get(r["id"], r["snippet"]), q)})
            link = lambda s: "/policies?" + urlencode({k: v for k, v in (("q", q), ("section", s)) if v})  # noqa: E731
            sections = [{"name": n, "count": c, "href": link(n), "current": n == sec} for n, c in counts.items()]
            return page(request, conn, "policies.html", q=q, sec=sec, groups=groups, n=len(found), total=len(every), sections=sections,
                        all_href=link(""))

    @app.get("/audit", response_class=HTMLResponse)
    def audit_log(request: Request):
        allowed = current_actor(request).role == "team_lead"  # a notice, not a 403 page, for everyone else
        with db() as conn:
            ctx = {}
            if allowed:
                broken = audit.verify_chain(conn)
                everything = conn.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
                ctx = {**audit_rows(conn, request.query_params), "chain_ok": broken is None,
                       "chain": f"Chain verified, {everything:,} entries" if broken is None else f"Chain broken at entry {broken}"}
            return page(request, conn, "audit.html", allowed=allowed, **ctx)

    @app.get("/audit/rows", response_class=HTMLResponse)
    def audit_more(request: Request):
        """The next page of rows for Load older. Team lead only, like the page."""
        if current_actor(request).role != "team_lead":
            return PlainTextResponse("The audit log is for the team lead.", status_code=403)
        with db() as conn:
            return templates.TemplateResponse(request, "partials/ref_audit_rows.html", audit_rows(conn, request.query_params))

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
                models = ensure_models(conn, cfg, x.models_dir if x.models_dir is not None else MODELS_DIR)
                cid = receive(conn, text=text, source=source, cfg=cfg, models=models, actor_id=actor.id, role=actor.role)
        except IntakeError as e:
            return settings_page(request, status=400, error=str(e), text=text, source=source)
        return settings_page(request, added=cid)
