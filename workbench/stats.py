"""Aggregate queries for the dashboards. Each is one or two grouped queries, never one per row."""
from datetime import date, timedelta

from .deadlines import due_soon_edge

OPEN = "state != 'accepted'"
HOURS = range(8, 19)


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


def deadline_buckets(conn, today, holidays, limit=5) -> list[tuple[str, int]]:
    h = headline(conn, today, holidays, limit)
    return [("Past deadline", h["past_deadline"]), ("Due soon", h["due_soon"]), ("Later", h["open"] - h["past_deadline"] - h["due_soon"])]


def needs_attention(conn, actor, today, limit=5) -> list[dict]:
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


def heatmap(conn) -> list[list[int]]:
    """Cases received by weekday (Monday first) and hour 8 to 18."""
    grid = [[0] * len(HOURS) for _ in range(7)]
    for d, h, n in conn.execute("SELECT (CAST(strftime('%w', received_at) AS INTEGER) + 6) % 7, CAST(strftime('%H', received_at) AS INTEGER), COUNT(*)"
                                " FROM cases GROUP BY 1, 2"):
        if h in HOURS:
            grid[d][h - HOURS.start] = n
    return grid


def by_department(conn):
    return conn.execute(f"SELECT department, COUNT(*) open, COALESCE(SUM(urgent = 1),0) urgent FROM cases"
                        f" WHERE {OPEN} AND department IS NOT NULL GROUP BY department ORDER BY open DESC, department").fetchall()


def by_stage(conn) -> list[tuple[str, int]]:
    return [tuple(r) for r in conn.execute("SELECT state, COUNT(*) FROM cases GROUP BY state ORDER BY MIN(CASE state WHEN 'new' THEN 0"
                                           " WHEN 'in_review' THEN 1 WHEN 'handed_over' THEN 2 WHEN 'returned' THEN 3 ELSE 4 END)")]


def complaint_map(conn) -> list[tuple[str, str, int]]:
    return [tuple(r) for r in conn.execute(f"SELECT department, type, COUNT(*) FROM cases WHERE {OPEN} AND department IS NOT NULL"
                                           " AND type IS NOT NULL GROUP BY 1, 2 ORDER BY 3 DESC, 1, 2")]


def pipeline_flow(conn, cfg) -> list[dict]:
    q = ("SELECT from_state, to_state, COUNT(*) FROM events WHERE from_state IS NOT NULL AND to_state IS NOT NULL AND from_state != to_state"
         " GROUP BY 1, 2 ORDER BY 1, 2")
    return [{"from": f, "to": t, "kind": "return" if t == "returned" else "forward", "count": n} for f, t, n in conn.execute(q)]


def team(conn, today, holidays):
    return conn.execute(f"SELECT s.id, s.name, COUNT(c.id) open, COALESCE(SUM(c.deadline < ?),0) past_deadline, COALESCE(SUM(c.urgent = 1),0) urgent"
                        f" FROM staff s LEFT JOIN cases c ON c.owner_id = s.id AND c.{OPEN} WHERE s.role = 'handler' GROUP BY s.id ORDER BY s.id",
                        (str(today),)).fetchall()


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
    if kind == "bars":
        items = data["items"]
        top = max(items, key=lambda i: i[1])
        return f"{data['title']}: {', '.join(f'{k} {v}' for k, v in items)}. Highest is {top[0]} with {top[1]}."
    raise ValueError(kind)
