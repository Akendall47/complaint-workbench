"""Aggregate queries for the dashboards. Each is one or two grouped queries, never one per row."""
import json
from datetime import date, timedelta

from .deadlines import due_soon_edge
from .handover import missing_fields

OPEN = "state != 'accepted'"
HOURS = range(8, 19)
ALL_HOURS = range(24)
OPEN_STAGES = ("new", "in_review", "handed_over", "returned")
COUNTABLE = {"source", "type", "state", "department"}  # the only columns count_by may group by (they go into SQL text)


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


def snapshot(conn, at, holidays, limit=5) -> dict | None:
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


def count_by(conn, col, department=None, source="", type_="") -> list[tuple[str, int]]:
    """Open cases grouped by one column, largest first. Empty values are left out."""
    if col not in COUNTABLE:
        raise ValueError(col)
    extra, args = _slice(source, type_)
    if department:
        extra, args = extra + " AND department = ?", args + [department]
    return [tuple(r) for r in conn.execute(f"SELECT {col}, COUNT(*) FROM cases WHERE {OPEN} AND {col} IS NOT NULL{extra} GROUP BY 1 ORDER BY 2 DESC, 1", args)]


def complaint_map(conn) -> list[tuple[str, str, int]]:
    """Open cases by department and type, largest first."""
    return [tuple(r) for r in conn.execute(f"SELECT department, type, COUNT(*) FROM cases WHERE {OPEN} AND department IS NOT NULL"
                                           " AND type IS NOT NULL GROUP BY 1, 2 ORDER BY 3 DESC, 1, 2")]


def department_weekly(conn, today, weeks=8) -> dict[str, list[int]]:
    """New complaints per department in each 7-day window ending today, oldest first. Departments with none are left out."""
    q = ("SELECT department, CAST((julianday(?) - julianday(substr(received_at,1,10))) / 7 AS INTEGER), COUNT(*) FROM cases"
         " WHERE department IS NOT NULL AND julianday(?) - julianday(substr(received_at,1,10)) BETWEEN 0 AND ? GROUP BY 1, 2")
    out = {}
    for d, b, n in conn.execute(q, (str(today), str(today), 7 * weeks - 1)):
        out.setdefault(d, [0] * weeks)[weeks - 1 - b] = n
    return out


def stage_rows(conn, today, department=None) -> list[dict]:
    """Open cases and those past deadline at each open stage, in pipeline order."""
    extra, args = (" AND department = ?", [department]) if department else ("", [])
    got = {s: (n, p) for s, n, p in conn.execute(f"SELECT state, COUNT(*), COALESCE(SUM(deadline < ?),0) FROM cases WHERE {OPEN}{extra} GROUP BY 1",
                                                 (str(today), *args))}
    return [{"state": s, "open": got.get(s, (0, 0))[0], "past": got.get(s, (0, 0))[1]} for s in OPEN_STAGES]


def team_activity(conn, today) -> dict:
    """Per person: cases they worked on that were accepted in the seven days ending today ("closed"), and their handovers
    with how many of those cases a specialist later returned ("returned": (handovers, returned))."""
    closed = dict(conn.execute("SELECT e.actor_id, COUNT(DISTINCT e.case_id) FROM events e JOIN cases c ON c.id = e.case_id"
                               " WHERE substr(c.accepted_at,1,10) BETWEEN ? AND ? GROUP BY 1", (str(today - timedelta(days=6)), str(today))).fetchall())
    ret = {a: (n, b) for a, n, b in conn.execute("SELECT h.actor_id, COUNT(DISTINCT h.case_id), COUNT(DISTINCT r.case_id) FROM events h"
                                                 " LEFT JOIN events r ON r.case_id = h.case_id AND r.to_state = 'returned' AND r.at > h.at"
                                                 " WHERE h.to_state = 'handed_over' GROUP BY 1")}
    return {"closed": closed, "returned": ret}


def incomplete_handovers(conn, cfg, department=None) -> tuple[int, int]:
    """(handed-over cases whose handover still lacks a required field, handed-over cases)."""
    extra, args = (" AND department = ?", [department]) if department else ("", [])
    bad = total = 0
    for d, raw in conn.execute(f"SELECT department, handover_json FROM cases WHERE handed_over_at IS NOT NULL AND department IS NOT NULL{extra}", args):
        total += 1
        bad += bool(missing_fields(d, json.loads(raw or "{}"), cfg))
    return bad, total


def handover_returns(conn) -> tuple[int, int]:
    """(handovers returned for more work, handovers made)."""
    back, ho = conn.execute("SELECT COALESCE(SUM(return_count > 0),0), COUNT(*) FROM cases WHERE handed_over_at IS NOT NULL").fetchone()
    return back, ho


def needs_attention(conn, actor, limit=5) -> list[dict]:
    """The cases that need this person: a handler's own live cases, a specialist's handovers, everything open for a team lead.
    Soonest deadline first, urgent before not urgent."""
    if actor.role == "handler":
        where, args = "state IN ('new','in_review','returned') AND owner_id = ?", [actor.id]
    elif actor.role == "specialist":
        where, args = "state = 'handed_over' AND department = (SELECT department FROM staff WHERE id = ?)", [actor.id]
    else:
        where, args = OPEN, []
    rows = conn.execute(f"SELECT id, type, department, deadline, urgent, state FROM cases WHERE {where}"
                        " ORDER BY deadline, urgent DESC, id LIMIT ?", (*args, limit)).fetchall()
    return [dict(r) for r in rows]


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


def team(conn, today, edge=None):
    """One row per handler and specialist, most cases past deadline first. The team lead is not a row: they share the work out.
    soon counts deadlines from today to the due-soon edge (none without an edge)."""
    return conn.execute(f"SELECT s.id, s.name, s.role, COUNT(c.id) open, COALESCE(SUM(c.deadline < ?),0) past_deadline, COALESCE(SUM(c.urgent = 1),0) urgent,"
                        f" COALESCE(SUM(c.deadline >= ? AND c.deadline <= ?),0) soon"
                        f" FROM staff s LEFT JOIN cases c ON c.owner_id = s.id AND c.{OPEN} WHERE s.role IN ('handler','specialist')"
                        " GROUP BY s.id ORDER BY past_deadline DESC, open DESC, s.id", (str(today), str(today), edge or "")).fetchall()


def unassigned(conn) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM cases WHERE {OPEN} AND owner_id IS NULL").fetchone()[0]


def _slice(source, type_):
    """SQL and arguments that narrow cases by source and type. Empty values do not narrow."""
    sql = "".join(f" AND {col} = ?" for col, v in (("source", source), ("type", type_)) if v)
    return sql, [v for v in (source, type_) if v]


NO_DEPARTMENT = "No department yet"


def department_rows(conn, cfg, today, source="", type_="") -> list[dict]:
    """Open, past deadline, due soon and urgent counts for every department, most past deadline first."""
    extra, args = _slice(source, type_)
    edge = str(due_soon_edge(today, cfg["urgent"]["deadline_within_business_days"], {date.fromisoformat(str(d)) for d in cfg["bank_holidays"]}))
    cols = "COUNT(*) open, COALESCE(SUM(deadline < ?),0) past, COALESCE(SUM(deadline >= ? AND deadline <= ?),0) soon, COALESCE(SUM(urgent = 1),0) urgent"
    got = {r["department"]: dict(r) for r in conn.execute(
        f"SELECT department, {cols} FROM cases WHERE {OPEN} AND department IS NOT NULL{extra} GROUP BY department", (str(today), str(today), edge, *args))}
    rows = [{"department": d, "open": 0, "past": 0, "soon": 0, "urgent": 0, **got.get(d, {})} for d in cfg["departments"]]
    none = conn.execute(f"SELECT {cols} FROM cases WHERE {OPEN} AND department IS NULL{extra}", (str(today), str(today), edge, *args)).fetchone()
    # last, so the totals add up to the open cases; the Queue has no filter for it, so the page shows plain text
    return sorted(rows, key=lambda r: (-r["past"], -r["open"], r["department"])) + [{"department": NO_DEPARTMENT, **dict(none)}]


def handovers(conn, department, source="", type_="", limit=10) -> tuple[list[dict], int]:
    """Cases waiting for a department, or for any department when it is None (soonest deadline first, at most limit), and how many wait."""
    extra, args = _slice(source, type_)
    if department:
        extra, args = " AND department = ?" + extra, [department, *args]
    where = f"state = 'handed_over'{extra}"
    n = conn.execute(f"SELECT COUNT(*) FROM cases WHERE {where}", args).fetchone()[0]
    rows = conn.execute(f"SELECT id, type, source, department, deadline, version FROM cases WHERE {where} ORDER BY deadline, id LIMIT ?", (*args, limit))
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
    """The pairs from rise_pairs with this week's count, the usual weekly count (the baseline weeks just before this one) and eight
    or more weekly counts to draw (oldest first, this week last)."""
    w = cfg["rise"]["baseline_weeks"]
    k = max(8, w + 1)
    pairs = rise_pairs(conn, {**cfg, "today": str(today)})
    if not pairs:
        return []
    q = ("SELECT department, type, CAST((julianday(?) - julianday(substr(received_at,1,10))) / 7 AS INTEGER) b, COUNT(*) FROM cases"
         " WHERE department IS NOT NULL AND type IS NOT NULL AND julianday(?) - julianday(substr(received_at,1,10)) BETWEEN 0 AND ?"
         " GROUP BY 1, 2, 3")
    per = {}
    for d, t, b, n in conn.execute(q, (str(today), str(today), 7 * k - 1)):
        if (d, t) in pairs:
            per.setdefault((d, t), [0] * k)[k - 1 - b] = n
    out = []
    for d, t in pairs:
        weekly = per[(d, t)]
        usual = sum(weekly[k - 1 - w:k - 1]) / w
        out.append({"department": d, "type": t, "this_week": weekly[-1], "usual": usual, "ratio": weekly[-1] / usual if usual else None, "weekly": weekly})
    return out


def sentence(kind, data) -> str:
    """The one plain sentence that says what a chart shows."""
    if kind in ("bars", "columns"):  # one sentence form, named for the chart it describes
        items = data["items"]
        top = max(items, key=lambda i: i[1])
        return f"{data['title']}: {', '.join(f'{k} {v}' for k, v in items)}. Highest is {top[0]} with {top[1]}."
    raise ValueError(kind)
