"""Queue: the work list, its filters, Load more, the preview pane and Assign to me."""
import json
from datetime import date
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .. import cases, drafts
from ..app import CASE_ID, PER_PAGE, safe_path
from ..cases import NotAllowed, StaleCase
from ..deadlines import business_days_left
from ..handover import missing_fields
from ..urgency import urgent_reasons
from .shared import STATE_NAME, current_actor, to_int

ORDER = "ORDER BY c.deadline, c.urgent DESC, c.id"


def may_assign(actor, c) -> bool:
    """Whether Assign to me would pass cases.assign: a handler or team lead taking an open case that has no owner."""
    return actor.role in cases.WORKERS and not c["owner_id"] and c["state"] != "accepted"


def short_date(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {d:%b %Y}"


def summary_state(draft_state, n: int, to_check: int) -> str:
    """The AI summary in a few words, so the preview says how much checking is left."""
    if n:
        return f"{n} claim{'s' * (n != 1)}, " + (f"{to_check} to check" if to_check else "all checked")
    return {"rejected": "Draft rejected", "invalid": "Draft could not be read"}.get(draft_state, "No draft yet")


def register(app, x):
    """Add the Queue routes. `x` carries what every page needs: cfg, today, hol, db, page, edge_of, templates."""
    cfg, today, hol, db, page, edge_of, templates = x.cfg, x.today, x.hol, x.db, x.page, x.edge_of, x.templates
    pay = cfg["deadlines"]["payment"]
    clock, clock_title = f"{pay['business_days']}-day clock", f"Payment services: {pay['business_days']} business days, {pay['extended_business_days']} in exceptional cases"

    def filters(actor, q: dict) -> dict:
        """The list filters from the query string. Unknown values fall back to the default view for the role."""
        one = lambda k: (q.get(k) or [""])[0]  # noqa: E731
        owner = one("owner")
        if owner not in ("me", "unassigned", "all"):
            owner = "me" if actor.role == "handler" else "all"
        return {"owner": owner, "department": one("department"), "type": one("type"), "state": one("state") or one("stage"),
                "urgent": "1" if one("urgent") == "1" else "", "due": one("due") if one("due") in ("past", "soon") else ""}

    def where(f: dict, actor, edge: str) -> tuple[str, list]:
        """SQL conditions for the filters. Without a stage filter only open cases show."""
        w, args = ["c.state = ?" if f["state"] else "c.state != 'accepted'"], [f["state"]] if f["state"] else []
        for col in ("department", "type"):
            if f[col]:
                w.append(f"c.{col} = ?"); args.append(f[col])  # noqa: E702
        if f["owner"] == "me":
            w.append("c.owner_id = ?"); args.append(actor.id)  # noqa: E702
        elif f["owner"] == "unassigned":
            w.append("c.owner_id IS NULL")
        if f["urgent"]:
            w.append("c.urgent = 1")
        if f["due"] == "past":
            w.append("c.state != 'accepted' AND c.deadline < ?"); args.append(cfg["today"])  # noqa: E702
        elif f["due"] == "soon":
            w.append("c.state != 'accepted' AND c.deadline >= ? AND c.deadline <= ?"); args += [cfg["today"], edge]  # noqa: E702
        return " AND ".join(w), args

    def preview(conn, actor, cid: str) -> dict | None:
        """The selected case in short: what it is, how urgent, how far along, and what this person may do."""
        c = conn.execute("SELECT * FROM cases WHERE id = ?", (cid,)).fetchone()
        if c is None:
            return None
        notes = conn.execute("SELECT author, written_at, body FROM notes WHERE case_id = ? ORDER BY seq", (cid,)).fetchall()
        reasons = [r for r in urgent_reasons(c, " ".join(n["body"] for n in notes), today, cfg) if "deadline" not in r.lower()] if c["urgent"] else []
        if c["urgent"] and c["urgent_manual"] is not None:
            reasons.append("Set by hand")
        n, to_check = conn.execute("SELECT COUNT(*), COALESCE(SUM(status = 'draft'), 0) FROM claims WHERE case_id = ? AND status != 'removed'",
                                   (cid,)).fetchone()
        missing = None
        if c["department"] in cfg["departments"]:
            missing = [m.replace("_", " ").capitalize() for m in missing_fields(c["department"], json.loads(c["handover_json"] or "{}"), cfg)]
        last = None
        if notes:  # masked as on the Case page; the panel shows its first two lines
            last = {"at": short_date(notes[-1]["written_at"] or c["received_at"]), "author": notes[-1]["author"],
                    "body": drafts.masked_notes(conn, cid, cfg)[-1][2][:400]}
        by_person = conn.execute("SELECT 1 FROM audit WHERE case_id = ? AND action = 'set_department' LIMIT 1", (cid,)).fetchone()
        return {"c": c, "days": business_days_left(date.fromisoformat(c["deadline"]), today, hol), "due": short_date(c["deadline"]),
                "received": short_date(c["received_at"]), "reasons": reasons, "summary": summary_state(c["draft_state"], n, to_check),
                "missing": missing, "dept_by": "a person" if by_person else "the model", "last": last, "assign": may_assign(actor, c)}

    def listing(conn, actor, q: dict, edge: str, sel: str | None = None) -> dict:
        """Everything the Queue shows: one page of rows, the count, the links, and the selected case's preview with its next row."""
        f = filters(actor, q)
        w, args = where(f, actor, edge)
        ids = [r[0] for r in conn.execute(f"SELECT c.id FROM cases c WHERE {w} {ORDER}", args)]  # one cheap query: count, order and next row
        total = len(ids)
        pages = max(1, -(-total // PER_PAGE))
        pg = min(max(1, to_int((q.get("page") or [""])[0], 1)), pages)
        got = conn.execute(f"SELECT c.*, s.name AS owner_name FROM cases c LEFT JOIN staff s ON s.id = c.owner_id WHERE {w} {ORDER} LIMIT ? OFFSET ?",
                           (*args, PER_PAGE, (pg - 1) * PER_PAGE)).fetchall()
        rows = [{"c": r, "days": business_days_left(date.fromisoformat(r["deadline"]), today, hol), "assign": may_assign(actor, r)} for r in got]
        keep = {k: v for k, v in f.items() if v}
        link = lambda **kw: "/queue?" + urlencode({**keep, **{k: v for k, v in kw.items() if v}})  # noqa: E731
        if not (sel and CASE_ID.match(sel)):
            sel = rows[0]["c"]["id"] if rows else None
        nxt = (ids[ids.index(sel) + 1] if ids.index(sel) + 1 < total else None) if sel in ids else (ids[0] if ids else None)
        return {"rows": rows, "f": f, "page_no": pg, "pages": pages, "total": total, "link": link, "qs": urlencode(keep),
                "more_qs": urlencode({**keep, "page": pg + 1}), "state_name": STATE_NAME, "clock": clock, "clock_title": clock_title, "sel": sel,
                "pv": preview(conn, actor, sel) if sel else None, "next_id": nxt, "filtered": bool(keep.keys() - {"owner"}),
                "sel_opts": {"departments": list(cfg["departments"]), "types": cfg["types"], "states": list(STATE_NAME)}}

    @app.get("/queue", response_class=HTMLResponse)
    def queue(request: Request):
        q = parse_qs(request.url.query)
        with db() as conn:
            return page(request, conn, "queue.html", **listing(conn, current_actor(request), q, edge_of(request), (q.get("case") or [None])[0]))

    @app.get("/queue/more", response_class=HTMLResponse)
    def more(request: Request):
        """Load more: the next page of rows, a new Load more row and the new count."""
        with db() as conn:
            ctx = listing(conn, current_actor(request), parse_qs(request.url.query), edge_of(request))
        return templates.TemplateResponse(request, "partials/queue_rows.html", {**ctx, "sel": None, "appended": True})

    @app.get("/queue/preview/{case_id}", response_class=HTMLResponse)
    def queue_preview(request: Request, case_id: str):
        """One case in the Preview panel. Without script it is the whole Queue page with that case selected."""
        q = parse_qs(request.url.query)
        with db() as conn:
            ctx = listing(conn, current_actor(request), q, edge_of(request), case_id)
            if ctx["pv"] is None or ctx["sel"] != case_id:
                if request.headers.get("HX-Request"):
                    return HTMLResponse('<p class="notice" role="alert">Case not found</p>', status_code=404)
                return page(request, conn, "not_found.html", status=404)
            if not request.headers.get("HX-Request"):
                return page(request, conn, "queue.html", **ctx)
        # The Next case link moves the row selection too; a row radio (name "pick") already has it.
        oob = request.headers.get("HX-Trigger-Name") != "pick"
        return templates.TemplateResponse(request, "partials/queue_preview.html", {**ctx, "oob": oob})

    @app.post("/cases/{case_id}/assign")
    def assign(request: Request, case_id: str, version: str = Form(""), next: str = Form("/queue")):
        """Assign to me from a row or the preview, then back to the same list. A refusal shows the Queue with a plain message."""
        actor, nxt = current_actor(request), safe_path(next) or "/queue"
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
                            message=str(e), **listing(conn, actor, q, edge_of(request)))
