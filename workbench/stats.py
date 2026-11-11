"""Aggregate queries for the dashboards. Each is one or two grouped queries, never one per row."""
import json
from datetime import date, timedelta

from .deadlines import add_business_days, due_soon_edge
from .handover import missing_fields

OPEN = "state != 'accepted'"
HOURS = range(8, 19)
ALL_HOURS = range(24)


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


def headline(conn, today, holidays, limit=5) -> dict:
    """Open, due soon, past deadline, typical (median) days open, and the share of handed-over cases that came back."""
    t, edge = str(today), str(due_soon_edge(today, limit, holidays))
    n, past, soon = conn.execute(f"SELECT COUNT(*), COALESCE(SUM(deadline < ?),0), COALESCE(SUM(deadline >= ? AND deadline <= ?),0)"
                                 f" FROM cases WHERE {OPEN}", (t, t, edge)).fetchone()
    days = [r[0] for r in conn.execute(f"SELECT julianday(?) - julianday(substr(received_at,1,10)) FROM cases WHERE {OPEN}"
                                       " ORDER BY 1 LIMIT 2 - ? % 2 OFFSET (? - 1) / 2", (t, n, n))] if n else []
    ho, back = conn.execute("SELECT COUNT(*), COALESCE(SUM(return_count > 0),0) FROM cases WHERE handed_over_at IS NOT NULL").fetchone()
    return {"open": n, "due_soon": soon, "past_deadline": past, "avg_days_open": sum(days) / len(days) if days else None,
            "returned_share": back / ho if ho else None}


def _snapshot(conn, at, holidays, limit=5) -> dict | None:
    """The Today figures as the data stood at the end of day `at`: a case was open if it had arrived and was not yet accepted.
    The returned share counts handover and return events up to then. None when no case had arrived by then."""
    t = str(at)
    if not conn.execute("SELECT 1 FROM cases WHERE substr(received_at,1,10) <= ? LIMIT 1", (t,)).fetchone():
        return None
    edge = str(due_soon_edge(at, limit, holidays))
    was_open = "substr(received_at,1,10) <= ? AND (accepted_at IS NULL OR substr(accepted_at,1,10) > ?)"
    n, past, soon = conn.execute(f"SELECT COUNT(*), COALESCE(SUM(deadline < ?),0), COALESCE(SUM(deadline >= ? AND deadline <= ?),0)"
                                 f" FROM cases WHERE {was_open}", (t, t, edge, t, t)).fetchone()
    days = sorted(r[0] for r in conn.execute(f"SELECT julianday(?) - julianday(substr(received_at,1,10)) FROM cases WHERE {was_open}", (t, t, t)))
    mid = (days[(n - 1) // 2] + days[n // 2]) / 2 if n else None
    ho, back = conn.execute("SELECT COUNT(DISTINCT CASE WHEN to_state = 'handed_over' THEN case_id END), COUNT(DISTINCT CASE WHEN to_state = 'returned'"
                            " THEN case_id END) FROM events WHERE substr(at,1,10) <= ?", (t,)).fetchone()
    return {"open": n, "past_deadline": past, "due_soon": soon, "avg_days_open": mid, "returned_share": back / ho if ho else None}


def daily(conn, today, days=30) -> list[tuple[str, int]]:
    """New complaints on each of the last `days` days, oldest first, days with none included."""
    start = today - timedelta(days=days - 1)
    got = dict(conn.execute("SELECT substr(received_at,1,10), COUNT(*) FROM cases WHERE substr(received_at,1,10) BETWEEN ? AND ? GROUP BY 1",
                            (str(start), str(today))).fetchall())
    return [(d, got.get(d, 0)) for d in (str(start + timedelta(days=i)) for i in range(days))]


def headline_change(conn, today, holidays, limit=5, days=7) -> dict:
    """Each headline figure now minus the same figure `days` days earlier. Both ends are worked out the same way (_snapshot: a case
    was open if received and not yet accepted, returns come from the events table), never from today's state. A key is None when
    either end has no figure: no case had arrived by then (all keys), no case was open (typical days) or no handover yet (returned share)."""
    keys = ("open", "due_soon", "past_deadline", "avg_days_open", "returned_share")
    now, then = _snapshot(conn, today, holidays, limit), _snapshot(conn, today - timedelta(days=days), holidays, limit)
    if not now or not then:
        return dict.fromkeys(keys)
    return {k: None if now[k] is None or then[k] is None else now[k] - then[k] for k in keys}


def _open_by(conn, col, department) -> list[tuple[str, int]]:
    """Open cases per value of col (a literal column name from this module), most first, ties by key. Empty values are left out."""
    extra, args = (" AND department = ?", [department]) if department else ("", [])
    return [tuple(r) for r in conn.execute(f"SELECT {col}, COUNT(*) FROM cases WHERE {OPEN} AND {col} IS NOT NULL{extra} GROUP BY 1 ORDER BY 2 DESC, 1", args)]


def by_source(conn, department="") -> list[tuple[str, int]]:
    """Open cases per source key, most first. department="" counts every open case, with or without a department."""
    return _open_by(conn, "source", department)


def by_type(conn, department="") -> list[tuple[str, int]]:
    """Open cases per type key, most first. department="" counts every open case, with or without a department."""
    return _open_by(conn, "type", department)


def complaint_map(conn) -> list[tuple[str, str, int]]:
    """Open cases by department and type (both set), largest first."""
    return [tuple(r) for r in conn.execute(f"SELECT department, type, COUNT(*) FROM cases WHERE {OPEN} AND department IS NOT NULL"
                                           " AND type IS NOT NULL GROUP BY 1, 2 ORDER BY 3 DESC, 1, 2")]


def department_table(conn, cfg, today, holidays, limit=5, weeks=8) -> list[dict]:
    """Open, past deadline and due soon for every department in cfg, and complaints received in each 7-day window ending today
    (the windows of trend, oldest first). Most past deadline first, then most open, then name. No "No department yet" row."""
    t, edge = str(today), str(due_soon_edge(today, limit, holidays))
    got = {d: (n, p, s) for d, n, p, s in conn.execute(
        "SELECT department, COUNT(*), COALESCE(SUM(deadline < ?),0), COALESCE(SUM(deadline >= ? AND deadline <= ?),0) FROM cases"
        f" WHERE {OPEN} AND department IS NOT NULL GROUP BY 1", (t, t, edge))}
    weekly = {}
    for d, b, n in conn.execute("SELECT department, CAST((julianday(?) - julianday(substr(received_at,1,10))) / 7 AS INTEGER), COUNT(*) FROM cases"
                                " WHERE department IS NOT NULL AND julianday(?) - julianday(substr(received_at,1,10)) BETWEEN 0 AND ? GROUP BY 1, 2",
                                (t, t, 7 * weeks - 1)):
        weekly.setdefault(d, [0] * weeks)[weeks - 1 - b] = n
    rows = [{"department": d, "open": got.get(d, (0, 0, 0))[0], "past": got.get(d, (0, 0, 0))[1], "soon": got.get(d, (0, 0, 0))[2],
             "weekly": weekly.get(d, [0] * weeks)} for d in cfg["departments"]]
    return sorted(rows, key=lambda r: (-r["past"], -r["open"], r["department"]))


def department_figures(conn, cfg, today, holidays, department="", limit=5) -> dict:
    """Open, past deadline and due soon for one department (every open case when department is ""), the share of its open cases
    at a specialist or sent back (handed_over, returned) that were returned at least once, and the field most often missing."""
    t, edge = str(today), str(due_soon_edge(today, limit, holidays))
    extra, args = (" AND department = ?", [department]) if department else ("", [])
    n, past, soon, ho, back = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(deadline < ?),0), COALESCE(SUM(deadline >= ? AND deadline <= ?),0),"
        " COALESCE(SUM(state IN ('handed_over','returned')),0), COALESCE(SUM(state IN ('handed_over','returned') AND return_count > 0),0)"
        f" FROM cases WHERE {OPEN}{extra}", (t, t, edge, *args)).fetchone()
    missing = missing_by_field(conn, cfg, department or None)
    return {"open": n, "past": past, "soon": soon, "incomplete_share": back / ho if ho else None, "top_missing": missing[0][0] if missing else None}


def handover_returns(conn) -> tuple[int, int]:
    """(handovers returned for more work, handovers made)."""
    back, ho = conn.execute("SELECT COALESCE(SUM(return_count > 0),0), COUNT(*) FROM cases WHERE handed_over_at IS NOT NULL").fetchone()
    return back, ho


def _attention(actor) -> tuple[str, list]:
    """The cases that need this person: a handler's own live cases, a specialist's handovers, everything open for a team lead."""
    if actor.role == "handler":
        return "state IN ('new','in_review','returned') AND owner_id = ?", [actor.id]
    if actor.role == "specialist":
        return "state = 'handed_over' AND department = (SELECT department FROM staff WHERE id = ?)", [actor.id]
    return OPEN, []


def needs_attention(conn, actor, limit=5, offset=0) -> list[dict]:
    """The cases that need this person (see _attention), soonest deadline first, urgent before not urgent; limit rows from offset."""
    where, args = _attention(actor)
    rows = conn.execute(f"SELECT id, type, department, deadline, urgent, state FROM cases WHERE {where}"
                        " ORDER BY deadline, urgent DESC, id LIMIT ? OFFSET ?", (*args, limit, offset)).fetchall()
    return [dict(r) for r in rows]


def due_by_day(conn, today, holidays, days=6) -> list[tuple[str, int]]:
    """Open cases due on each of `days` business days, today first when today is a business day (ISO date, count).
    A deadline on a weekend or bank holiday counts on the business day before it, the last day to act. With the default,
    the counts add up to headline's due_soon (today to five business days ahead)."""
    first = today if add_business_days(today - timedelta(days=1), 1, holidays) == today else add_business_days(today, 1, holidays)
    dates = [first] + [add_business_days(first, i, holidays) for i in range(1, days)]
    out = {str(d): 0 for d in dates}
    for deadline, n in conn.execute(f"SELECT deadline, COUNT(*) FROM cases WHERE {OPEN} AND deadline BETWEEN ? AND ? GROUP BY 1",
                                    (str(today), str(dates[-1]))):
        out[max((d for d in out if d <= deadline), default=str(first))] += n
    return list(out.items())


def draft_checks(conn) -> dict:
    """What the checks found in the AI-drafted claims: the quote was found word for word in the notes ("found"), the claim is an
    inference marked for the handler to check ("inferred"), or no matching quote was found so the claim is blocked ("missing")."""
    found, inferred, missing, drafts = conn.execute(
        "SELECT COALESCE(SUM(supported = 1 AND inferred = 0),0), COALESCE(SUM(supported = 1 AND inferred = 1),0), COALESCE(SUM(supported = 0),0),"
        " COUNT(DISTINCT case_id) FROM claims").fetchone()
    return {"found": found, "inferred": inferred, "missing": missing, "drafts": drafts}


def attention_count(conn, actor) -> int:
    """How many cases need_attention would list without a limit."""
    where, args = _attention(actor)
    return conn.execute(f"SELECT COUNT(*) FROM cases WHERE {where}", args).fetchone()[0]


def trend(conn, today, weeks=8) -> list[dict]:
    """New and closed complaints per 7-day window ending today, oldest first."""
    def counts(col):
        q = (f"SELECT CAST((julianday(?) - julianday(substr({col},1,10))) / 7 AS INTEGER) b, COUNT(*) FROM cases"
             f" WHERE {col} IS NOT NULL AND julianday(?) - julianday(substr({col},1,10)) BETWEEN 0 AND ? GROUP BY b")
        return dict(conn.execute(q, (str(today), str(today), 7 * weeks - 1)).fetchall())
    new, closed = counts("received_at"), counts("accepted_at")
    return [{"week": str(today - timedelta(days=7 * b + 6)), "new": new.get(b, 0), "closed": closed.get(b, 0)} for b in range(weeks - 1, -1, -1)]


def heatmap(conn, hours=HOURS) -> list[list[int]]:
    """Cases received by weekday (Monday first) and hour, one column per hour in `hours` (8 to 18 by default; pass range(24)
    so night and evening arrivals count too)."""
    grid = [[0] * len(hours) for _ in range(7)]
    for d, h, n in conn.execute("SELECT (CAST(strftime('%w', received_at) AS INTEGER) + 6) % 7, CAST(strftime('%H', received_at) AS INTEGER), COUNT(*)"
                                " FROM cases GROUP BY 1, 2"):
        if h in hours:
            grid[d][h - hours.start] = n
    return grid


def by_department(conn):
    return conn.execute(f"SELECT department, COUNT(*) open, COALESCE(SUM(urgent = 1),0) urgent FROM cases"
                        f" WHERE {OPEN} AND department IS NOT NULL GROUP BY department ORDER BY open DESC, department").fetchall()


def by_stage(conn) -> list[tuple[str, int]]:
    return [tuple(r) for r in conn.execute("SELECT state, COUNT(*) FROM cases GROUP BY state ORDER BY MIN(CASE state WHEN 'new' THEN 0"
                                           " WHEN 'in_review' THEN 1 WHEN 'handed_over' THEN 2 WHEN 'returned' THEN 3 ELSE 4 END)")]


def team(conn, today, holidays=(), limit=5):
    """One row per handler and specialist, most cases past deadline first. The team lead is not a row: they share the work out.
    due_soon: open cases due from today to the due-soon edge. closed_week: cases they own that were accepted in the 7 days ending today."""
    t, edge = str(today), str(due_soon_edge(today, limit, set(holidays)))
    is_open = "c.state != 'accepted'"
    return conn.execute(f"SELECT s.id, s.name, s.role, COALESCE(SUM({is_open}),0) open, COALESCE(SUM({is_open} AND c.deadline < ?),0) past_deadline,"
                        f" COALESCE(SUM({is_open} AND c.urgent = 1),0) urgent, COALESCE(SUM({is_open} AND c.deadline >= ? AND c.deadline <= ?),0) due_soon,"
                        " COALESCE(SUM(c.state = 'accepted' AND substr(c.accepted_at,1,10) BETWEEN ? AND ?),0) closed_week"
                        " FROM staff s LEFT JOIN cases c ON c.owner_id = s.id WHERE s.role IN ('handler','specialist')"
                        " GROUP BY s.id ORDER BY past_deadline DESC, open DESC, s.id", (t, t, edge, str(today - timedelta(days=6)), t)).fetchall()


def unassigned(conn) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM cases WHERE {OPEN} AND owner_id IS NULL").fetchone()[0]


def _slice(source, type_):
    """SQL and arguments that narrow cases by source and type. Empty values do not narrow."""
    sql = "".join(f" AND {col} = ?" for col, v in (("source", source), ("type", type_)) if v)
    return sql, [v for v in (source, type_) if v]


NO_DEPARTMENT = "No department yet"


def department_rows(conn, cfg, today, source="", type_="") -> list[dict]:
    """Open, past deadline and urgent counts for every department, most past deadline first."""
    extra, args = _slice(source, type_)
    got = {r["department"]: dict(r) for r in conn.execute(
        "SELECT department, COUNT(*) open, COALESCE(SUM(deadline < ?),0) past, COALESCE(SUM(urgent = 1),0) urgent FROM cases"
        f" WHERE {OPEN} AND department IS NOT NULL{extra} GROUP BY department", (str(today), *args))}
    rows = [{"department": d, "open": 0, "past": 0, "urgent": 0, **got.get(d, {})} for d in cfg["departments"]]
    none = conn.execute("SELECT COUNT(*) open, COALESCE(SUM(deadline < ?),0) past, COALESCE(SUM(urgent = 1),0) urgent FROM cases"
                        f" WHERE {OPEN} AND department IS NULL{extra}", (str(today), *args)).fetchone()
    # last, so the totals add up to the open cases; the Queue has no filter for it, so the page shows plain text
    return sorted(rows, key=lambda r: (-r["past"], -r["open"], r["department"])) + [{"department": NO_DEPARTMENT, **dict(none)}]


def handovers(conn, department, source="", type_="", limit=10, offset=0) -> tuple[list[dict], int]:
    """Cases waiting for a department (soonest deadline first, at most limit from offset) and how many wait in all."""
    extra, args = _slice(source, type_)
    where = f"state = 'handed_over' AND department = ?{extra}"
    n = conn.execute(f"SELECT COUNT(*) FROM cases WHERE {where}", (department, *args)).fetchone()[0]
    rows = conn.execute(f"SELECT id, type, source, deadline, version FROM cases WHERE {where} ORDER BY deadline, id LIMIT ? OFFSET ?",
                        (department, *args, limit, offset))
    return [dict(r) for r in rows], n


def missing_by_field(conn, cfg, department, source="", type_="") -> list[tuple[str, int]]:
    """How many open cases of a department (of every department when it is None) lack each required field, most often missing first.
    Fields never missing are left out."""
    extra, args = _slice(source, type_)
    if department:
        extra, args = " AND department = ?" + extra, [department, *args]
    n = {}
    for d, raw in conn.execute(f"SELECT department, handover_json FROM cases WHERE {OPEN} AND department IS NOT NULL{extra}", args):
        for f in missing_fields(d, json.loads(raw or "{}"), cfg):
            n[f] = n.get(f, 0) + 1
    return sorted(((f.replace("_", " ").capitalize(), k) for f, k in n.items()), key=lambda x: (-x[1], x[0]))


def pipeline_paths(conn, cfg) -> list[dict]:
    """The paths in cfg["paths"] with how many cases took each. An urgent path counts urgent cases, a normal path the rest, any other
    kind all. Paths nobody took are left out. Urgency is the case's today, not what it was at the move."""
    n = {}
    for f, t, u, k in conn.execute("SELECT e.from_state, e.to_state, COALESCE(c.urgent, 0), COUNT(*) FROM events e LEFT JOIN cases c ON c.id = e.case_id"
                                   " WHERE e.from_state IS NOT NULL AND e.to_state IS NOT NULL AND e.from_state != e.to_state GROUP BY 1, 2, 3"):
        n[(f, t, u)] = k
    pick = {"urgent": lambda f, t: n.get((f, t, 1), 0), "normal": lambda f, t: n.get((f, t, 0), 0)}
    out = []
    for p in cfg["paths"]:
        count = pick.get(p["kind"], lambda f, t: n.get((f, t, 0), 0) + n.get((f, t, 1), 0))(p["from"], p["to"])
        if count:
            out.append({**p, "count": count})
    return out


def rises(conn, today, cfg) -> list[dict]:
    """The pairs from rise_pairs with this week's count, the usual weekly count and weekly counts (oldest first, this week last)."""
    w = cfg["rise"]["baseline_weeks"]
    pairs = rise_pairs(conn, {**cfg, "today": str(today)})
    if not pairs:
        return []
    q = ("SELECT department, type, CAST((julianday(?) - julianday(substr(received_at,1,10))) / 7 AS INTEGER) b, COUNT(*) FROM cases"
         " WHERE department IS NOT NULL AND type IS NOT NULL AND julianday(?) - julianday(substr(received_at,1,10)) BETWEEN 0 AND ?"
         " GROUP BY 1, 2, 3")
    per = {}
    for d, t, b, n in conn.execute(q, (str(today), str(today), 7 * (w + 1) - 1)):
        if (d, t) in pairs:
            per.setdefault((d, t), [0] * (w + 1))[w - b] = n
    out = []
    for d, t in pairs:
        weekly = per[(d, t)]
        usual = sum(weekly[:w]) / w
        out.append({"department": d, "type": t, "this_week": weekly[w], "usual": usual, "ratio": weekly[w] / usual if usual else None, "weekly": weekly})
    return out


def sentence(kind, data) -> str:
    """The one plain sentence that says what a chart shows."""
    if kind in ("bars", "columns"):  # one sentence form, named for the chart it describes
        items = data["items"]
        top = max(items, key=lambda i: i[1])
        return f"{data['title']}: {', '.join(f'{k} {v}' for k, v in items)}. Highest is {top[0]} with {top[1]}."
    raise ValueError(kind)
