"""Aggregate queries for the dashboards. Task 9 adds the rest."""
from datetime import date, timedelta


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
