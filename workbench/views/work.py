"""Departments, Team and Pipeline: workload by team, by person and by stage."""
import json
from datetime import date
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse

from .. import cases, flow, fluid, stats
from ..deadlines import business_days_left
from ..handover import missing_fields
from .shared import ROLE_NAME, STATE_NAME, current_actor

MORE = 20  # rows per "Load more"


def register(app, x):
    """Add the Departments, Team and Pipeline routes. `x` carries cfg, today, hol, db, page, edge_of, templates."""
    cfg, today, hol, db, page, templates = x.cfg, x.today, x.hol, x.db, x.page, x.templates
    lim = cfg["urgent"]["deadline_within_business_days"]

    def days(d):
        return business_days_left(date.fromisoformat(d), today, hol)

    def scope(conn, actor, q) -> tuple[str, str, str, bool]:
        """Department, channel and type to show. A specialist sees only their own department, whatever the link says."""
        row = conn.execute("SELECT department FROM staff WHERE id = ? AND role = 'specialist'", (actor.id,)).fetchone() if actor.role == "specialist" else None
        dept = row[0] if row and row[0] else (q.get("department") if q.get("department") in cfg["departments"] else "")
        source = q.get("source") if q.get("source") in cfg["sources"] else ""
        type_ = q.get("type") if q.get("type") in cfg["types"] else ""
        return dept, source, type_, bool(row and row[0])

    def handover_ctx(conn, actor, dept, source, type_, offset=0) -> dict:
        """One slice of the waiting handovers with what each row shows; the rules layer decides who gets Accept and Return."""
        rows, n = stats.handovers(conn, dept, source, type_, limit=MORE, offset=offset)
        for c in rows:
            c["days"] = days(c["deadline"])
            c["missing"] = ([f.replace("_", " ").capitalize() for f in missing_fields(c["department"], json.loads(c["handover_json"] or "{}"), cfg)]
                            if c["department"] in cfg["departments"] else None)  # None: no department, so no field list to check
            c["can"] = cases.can_decide(conn, c["id"], actor)[0]
        keep = {k: v for k, v in (("department", dept), ("source", source), ("type", type_)) if v}
        return {"rows": rows, "n": n, "next": offset + MORE, "act": actor.role == "specialist",
                "more": "/departments/handovers?" + urlencode({**keep, "offset": offset + MORE}),
                "queue_link": "/queue?" + urlencode({"owner": "all", "state": "handed_over", **({"department": dept} if dept else {})})}

    @app.get("/departments", response_class=HTMLResponse)
    def departments(request: Request):
        actor = current_actor(request)
        with db() as conn:
            dept, source, type_, own = scope(conn, actor, request.query_params)
            keep = {"department": dept, "source": source, "type": type_}
            link = lambda **kw: "/departments?" + urlencode({k: v for k, v in {**keep, **kw}.items() if v})  # noqa: E731
            rows = stats.department_rows(conn, cfg, today, source, type_)
            chips = [] if own else [("All", sum(r["open"] for r in rows), link(department=""), not dept)] + sorted(
                ((r["department"], r["open"], link(department=r["department"]), r["department"] == dept) for r in rows if r["department"] in cfg["departments"]),
                key=lambda c: -c[1])
            f = stats.department_figures(conn, cfg, today, hol, dept, lim, source, type_)
            # the Queue has no channel filter, so a channel-narrowed figure links nowhere rather than to a different number
            q = None if source else (lambda **kw: "/queue?" + urlencode({"owner": "all", **{k: v for k, v in (("department", dept), ("type", type_)) if v}, **kw}))  # noqa: E731
            figures = [("Open", f"{f['open']:,}", q and q(), False), ("Past deadline", f"{f['past']:,}", q and q(due="past"), f["past"] > 0),
                       (f"Due in {lim} business days", f"{f['soon']:,}", q and q(due="soon"), False),
                       ("Sent back", "–" if f["incomplete_share"] is None else f"{f['incomplete_share']:.0%}", None, False),
                       ("Most missing field", f["top_missing"] or "None", None, False)]
            return page(request, conn, "departments.html", dept=dept, own=own, chips=chips, figures=figures, source=source, type_=type_,
                        clear=lambda k: link(**{k: ""}),
                        channel=fluid.track([(s.capitalize(), n) for s, n in stats.by_source(conn, dept)], href=lambda s: link(source=s.lower())),
                        types=fluid.track(stats.by_type(conn, dept), href=lambda t: link(type=t)),
                        missing=fluid.track(stats.missing_by_field(conn, cfg, dept or None, source, type_)[:8]),
                        **handover_ctx(conn, actor, dept, source, type_))

    @app.get("/departments/handovers", response_class=HTMLResponse)
    def more_handovers(request: Request, offset: int = 0):
        """The next waiting handovers and a new Load more row, for htmx to put in place of the old one."""
        actor = current_actor(request)
        with db() as conn:
            dept, source, type_, _ = scope(conn, actor, request.query_params)
            ctx = handover_ctx(conn, actor, dept, source, type_, max(0, offset))
        return templates.TemplateResponse(request, "partials/work_handover_rows.html", ctx)

    @app.get("/team", response_class=HTMLResponse)
    def team(request: Request):
        actor = current_actor(request)
        with db() as conn:
            back = stats.returned_by_handler(conn)
            people = [{**dict(r), "back": back.get(r["id"], (0, 0)) if r["role"] == "handler" else None}
                      for r in sorted(stats.team(conn, today, hol, lim), key=lambda r: (r["role"] != "handler", r["name"]))]  # by role and name: no ranking
            avg = {}
            for role in ("handler", "specialist"):
                grp = [p for p in people if p["role"] == role] or [{"open": 0, "past_deadline": 0, "due_soon": 0, "closed_week": 0, "back": (0, 0)}]
                avg[role] = {k: sum(p[k] for p in grp) / len(grp) for k in ("open", "past_deadline", "due_soon", "closed_week")}
                avg[role]["back"] = tuple(map(sum, zip(*(p["back"] for p in grp)))) if role == "handler" else None
            lead = actor.role == "team_lead"
            rows = people if lead else [p for p in people if p["id"] == actor.id] + [{**avg.get(actor.role, avg["handler"]), "id": "", "name": "Team average", "role": actor.role}]
            top = max([p["open"] for p in people] + [1])
            return page(request, conn, "team.html", rows=rows, avg=avg, top=top, role_name=ROLE_NAME, figures=stats.team_figures(conn, today, hol, lim), lim=lim,
                        **unassigned_ctx(conn, actor))

    def unassigned_ctx(conn, actor, offset=0) -> dict:
        """One slice of the Unassigned list. Only roles the rules layer lets assign (handlers to themselves, the team lead) get the button."""
        rows = [{**c, "days": days(c["deadline"])} for c in stats.unassigned_cases(conn, MORE, offset)]
        return {"unassigned": rows, "n_unassigned": stats.unassigned(conn), "next": offset + MORE, "can_assign": actor.role in cases.WORKERS}

    @app.get("/team/unassigned", response_class=HTMLResponse)
    def more_unassigned(request: Request, offset: int = 0):
        """The next unassigned cases and a new Load more item, for htmx to put in place of the old one."""
        with db() as conn:
            ctx = unassigned_ctx(conn, current_actor(request), max(0, offset))
        return templates.TemplateResponse(request, "partials/work_unassigned_items.html", ctx)

    @app.get("/pipeline", response_class=HTMLResponse)
    def pipeline(request: Request):
        name = lambda s: STATE_NAME.get(s, s.replace("_", " ").capitalize())  # noqa: E731
        key = {name(s): s for s in cfg["stages"]}
        href = lambda s: "/queue?" + urlencode({"owner": "all", "state": s})  # noqa: E731
        d, p, r = cfg["deadlines"], cfg["deadlines"]["payment"], cfg["rise"]
        rules = [f"Deadline: {d['other']['weeks']} weeks from arrival.",
                 f"Payment services: {p['business_days']} business days, {p['extended_business_days']} in exceptional cases.",
                 f"Urgent: due within {lim} business days, or notes show vulnerability, hardship or fraud.",
                 f"Unusual rise: {r['minimum_cases']}+ cases of one department and type in a week, {r['ratio']:g}x its {r['baseline_weeks']}-week average."]
        with db() as conn:
            n = dict(stats.by_stage(conn))
            stages = [{"key": s, "label": name(s), "count": n.get(s, 0), "note": "closed" if s == "accepted" else "here now", "href": href(s),
                       "row": "below" if s == "returned" else "main"} for s in cfg["stages"]]
            chart = flow.case_flow(stages, stats.pipeline_paths(conn, cfg), "Case flow", "How cases move between stages; band width is the number of cases")
            return page(request, conn, "pipeline.html", chart=chart, rules=rules,
                        by_stage=fluid.track([(name(s), n.get(s, 0)) for s in cfg["stages"]], cls=lambda k: "st-" + key[k], href=lambda k: href(key[k])))
