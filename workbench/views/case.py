"""Case: one complaint, the AI summary checks, the handover and the decision.
Routes never change a case themselves; they call workbench.cases and show its NotAllowed and StaleCase messages as plain text."""
from datetime import date

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from .. import case_view, cases, drafts
from ..app import CASE_ID
from ..cases import NotAllowed, StaleCase
from .shared import STATE_NAME, current_actor, to_int

RECENT = 5
LIST_NAME = {"handler": "Your open cases", "specialist": "Handovers to your department", "team_lead": "All open cases"}


def recent_ids(cookie: str, case_id: str) -> list[str]:
    """The cases opened last, newest first, from the `recent` cookie. Only well-formed ids are kept, so the cookie cannot inject anything."""
    old = [i for i in (cookie or "").split(".") if CASE_ID.match(i) and i != case_id]
    return [case_id, *dict.fromkeys(old)][:RECENT]


def recent_tabs(conn, ids: list[str]) -> list[dict]:
    """Each recent case with its stage for the dot, in cookie order. Cases that no longer exist drop out. One query."""
    state = dict(conn.execute(f"SELECT id, state FROM cases WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall())
    return [{"id": i, "state": state[i]} for i in ids if i in state]


def neighbours(conn, actor, case_id: str) -> dict:
    """Previous and next in this person's own list, in Queue order, and where this case sits. One query with window functions.
    A case outside the list gets no position, and Next goes to the first case of the list."""
    if actor.role == "handler":
        where, args = "owner_id = ? AND state != 'accepted'", [actor.id]
    elif actor.role == "specialist":
        where, args = "state = 'handed_over' AND department = (SELECT department FROM staff WHERE id = ?)", [actor.id]
    else:
        where, args = "state != 'accepted'", []
    r = conn.execute(f"""SELECT id, pos, n, prev, nxt FROM (
        SELECT id, ROW_NUMBER() OVER w AS pos, COUNT(*) OVER () AS n, LAG(id) OVER w AS prev, LEAD(id) OVER w AS nxt
        FROM cases WHERE {where} WINDOW w AS (ORDER BY deadline, urgent DESC, id))
        WHERE id = ? OR pos = 1 ORDER BY id = ? DESC LIMIT 1""", (*args, case_id, case_id)).fetchone()
    name = LIST_NAME[actor.role]
    if r is None:
        return {"n": 0, "pos": None, "prev": None, "next": None, "name": name}
    if r["id"] != case_id:
        return {"n": r["n"], "pos": None, "prev": None, "next": r["id"], "name": name}
    return {"n": r["n"], "pos": r["pos"], "prev": r["prev"], "next": r["nxt"], "name": name}


def register(app, x):
    """Add the Case routes. `x` carries what every page needs: cfg, today, hol, db, page, edge_of, templates."""
    cfg, db, page, templates = x.cfg, x.db, x.page, x.templates

    def gone(request):
        """The case does not exist. A swap target gets a small fragment, a page the not-found page."""
        if request.headers.get("HX-Request"):
            return HTMLResponse('<div id="case" tabindex="-1" hx-history="false"><p class="notice" role="alert">Case not found</p></div>', status_code=404)
        with db() as conn:
            return page(request, conn, "not_found.html", status=404)

    def case_response(request, case_id, step=1, all_=False, message=None, status=200, unmasked=False):
        """The case as a page, or as the #case fragment for htmx. The page also carries the recent-case tabs and Previous and Next."""
        if not CASE_ID.match(case_id):
            return gone(request)
        actor, recent = current_actor(request), None
        with db() as conn:
            v = case_view.build(conn, cfg, case_id, actor, step, all_, unmasked)
            if v is None:
                return gone(request)
            due = date.fromisoformat(v["c"]["deadline"])
            ctx = {"v": v, "state_name": STATE_NAME, "message": message, "stale": status == 409, "case_now": case_id, "due_on": f"{due.day} {due:%b}"}
            if request.headers.get("HX-Request"):
                resp = templates.TemplateResponse(request, "partials/case_main.html", {"actor": actor, "cfg": cfg, **ctx}, status_code=status)
            else:
                recent = recent_ids(request.cookies.get("recent", ""), case_id)
                resp = page(request, conn, "case.html", status=status, recent=recent_tabs(conn, recent), near=neighbours(conn, actor, case_id), **ctx)
        if unmasked:
            resp.headers["Cache-Control"] = "no-store"  # unmasked text is never kept in a cache
        resp.set_cookie("last_case", case_id, samesite="lax")
        if recent:
            resp.set_cookie("recent", ".".join(recent), samesite="lax", httponly=True)
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
        """Return, reject, unmask and the urgent flag are logged with a reason, so an empty one is refused."""
        if not (reason or "").strip():
            raise NotAllowed("Enter a reason")
        return reason

    def simple(name, fn_name):
        """A route for an action that needs only the case version."""
        @app.post("/cases/{case_id}/" + name)
        def _(request: Request, case_id: str, version: str = Form(""), step: str = Form("1"), all: str = Form("0")):
            return act(request, case_id, version, step, all, lambda c, a, v: getattr(cases, fn_name)(c, case_id, a, v))
    for n, f in (("open", "open_case"), ("approve", "approve"), ("accept", "accept")):
        simple(n, f)

    def with_reason(name, fn_name):
        """A route for an action that must carry a reason."""
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
