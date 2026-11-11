"""Overview: the morning check. Today's figures, what is coming due, where complaints come from and what needs this person."""
from datetime import date, timedelta
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse

from .. import fluid, stats
from ..deadlines import business_days_left
from ..urgency import urgent_reasons
from .shared import STATE_NAME, current_actor, strip


def register(app, x):
    """Add the Overview routes. `x` carries what every page needs: cfg, today, hol, db, page, edge_of, templates."""
    cfg, today, hol, db, page, edge_of, templates = x.cfg, x.today, x.hol, x.db, x.page, x.edge_of, x.templates
    STATE_KEY = {v: k for k, v in STATE_NAME.items()}

    def change(d, unit="") -> tuple[str, str] | None:
        """A chip comparing a figure with seven days earlier. Lower is better for every Overview figure."""
        if d is None:
            return None
        then = today - timedelta(days=7)
        since = f"vs {then.day} {then:%b}"
        if d == 0:
            return f"no change {since}", "same"
        unit = unit.rstrip("s") if abs(d) == 1 else unit
        return f"{'up' if d > 0 else 'down'} {abs(d):,}{unit} {since}", "worse" if d > 0 else "better"

    def attention_rows(conn, actor, offset=0, limit=10) -> list[dict]:
        rows = stats.needs_attention(conn, actor, limit=limit, offset=offset)
        ids = [r["id"] for r in rows]
        text = dict(conn.execute(f"SELECT case_id, group_concat(body, ' ') FROM notes WHERE case_id IN ({','.join('?' * len(ids))}) GROUP BY case_id",
                                 ids).fetchall()) if ids else {}
        return [{**r, "days": business_days_left(date.fromisoformat(r["deadline"]), today, hol),  # the deadline chip shows the deadline reason
                 "why": [w for w in urgent_reasons(r, text.get(r["id"], ""), today, cfg) if "deadline" not in w.lower()]} for r in rows]

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request):
        actor, lim = current_actor(request), cfg["urgent"]["deadline_within_business_days"]
        q = lambda **kw: "/queue?" + urlencode({"owner": "all", **kw})  # noqa: E731
        short = lambda d: f"{date.fromisoformat(d).day} {date.fromisoformat(d):%b}"  # noqa: E731
        with db() as conn:
            h, ch, st = stats.headline(conn, today, hol, lim), stats.headline_change(conn, today, hol, lim), strip(conn, cfg, edge_of(request))
            pts = lambda v: None if v is None else round(100 * v)  # noqa: E731
            kpis = [("Past deadline", f"{h['past_deadline']:,}", q(due="past"), True, change(ch["past_deadline"])),
                    (f"Due in {lim} business days", f"{h['due_soon']:,}", q(due="soon"), False, change(ch["due_soon"])),
                    ("Urgent", f"{st['urgent']:,}", q(urgent="1"), False, None),
                    ("Open complaints", f"{h['open']:,}", q(), False, change(ch["open"])),
                    ("Typical days open", "–" if h["avg_days_open"] is None else f"{h['avg_days_open']:.0f}", None, False,
                     change(None if ch["avg_days_open"] is None else round(ch["avg_days_open"]), " days")),
                    ("Handovers returned", "–" if h["returned_share"] is None else f"{h['returned_share']:.0%}", None, False,
                     change(pts(ch["returned_share"]), " pts"))]
            ahead = [("Today" if d == str(today) else f"{date.fromisoformat(d):%a} {date.fromisoformat(d).day}", n) for d, n in stats.due_by_day(conn, today, hol, lim)]
            days = [(short(d), n) for d, n in stats.daily(conn, today)]
            peak = max(days, key=lambda x: x[1]) if days else ("", 0)
            stages = [(STATE_NAME[s], n) for s, n in stats.by_stage(conn)]
            rises = stats.rises(conn, today, cfg)
            checks = stats.draft_checks(conn)
            src = cfg.get("source_names", {})
            return page(request, conn, "overview.html", kpis=kpis, updated=st["updated"], q=q, rise=rises[0] if rises else None, n_rises=len(rises), rise_query=st["rise_query"],
                        ahead=fluid.cols(ahead, f"Open cases due on each of the next {lim} business days: " + ", ".join(f"{k} {v}" for k, v in ahead), hot=("Today",)),
                        ahead_total=sum(n for _, n in ahead),
                        daily=fluid.area(days, f"New complaints per day, last 30 days. Peak {peak[1]} on {peak[0]}."),
                        hours=fluid.heat(stats.heatmap(conn, stats.ALL_HOURS), stats.ALL_HOURS, "Complaints received by weekday and hour of day. Darker is busier."),
                        cmap=fluid.band_map(stats.complaint_map(conn), href=lambda d, t: q(department=d, type=t), label="Open complaints by department and type"),
                        stages=fluid.track(stages, cls=lambda k: "st-" + STATE_KEY[k], href=lambda k: q(state=STATE_KEY[k])),
                        attention=attention_rows(conn, actor), n_attention=stats.attention_count(conn, actor), next=10,
                        departments=[{**r, "spark": fluid.spark(r["weekly"], "Received per week, last 8 weeks: " + ", ".join(map(str, r["weekly"])))}
                                     for r in stats.department_table(conn, cfg, today, hol, lim)],
                        sources=fluid.track([(src.get(k, k.capitalize()), n) for k, n in stats.by_source(conn)]),
                        types=fluid.track(stats.by_type(conn), href=lambda t: q(type=t)),
                        checks=checks, check_chart=fluid.track([("Quote found", checks["found"]), ("Inference, to check", checks["inferred"]),
                                                                ("No quote, blocked", checks["missing"])], hot=("No quote, blocked",)))

    @app.get("/overview/attention", response_class=HTMLResponse)
    def more_attention(request: Request, offset: int = 0):
        actor, offset = current_actor(request), max(0, offset)
        with db() as conn:
            rows, n = attention_rows(conn, actor, offset=offset), stats.attention_count(conn, actor)
        return templates.TemplateResponse(request, "partials/attention_items.html", {"attention": rows, "next": offset + 10, "n_attention": n})
