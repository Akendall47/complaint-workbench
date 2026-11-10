from datetime import date, timedelta

from workbench.deadlines import business_days_left, due_soon_edge
from workbench.stats import rise_pairs


def test_due_soon_edge_is_last_date_within_limit(cfg):
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    today = date.fromisoformat(cfg["today"])
    edge = due_soon_edge(today, 5, hol)
    assert business_days_left(edge, today, hol) <= 5
    assert business_days_left(edge + timedelta(days=1), today, hol) > 5


def test_rise_pairs_needs_ratio_and_minimum(conn, cfg):
    def add(n, day, dept, typ, start):
        for i in range(n):
            conn.execute("INSERT INTO cases(id, received_at, state, department, type, deadline, version)"
                         " VALUES (?, ?, 'new', ?, ?, '2027-01-01', 0)", (f"{dept[:2]}{typ[:2]}{start + i}", f"{day}T10:00:00", dept, typ))
    add(12, "2026-11-09", "Bereavement", "Service", 0)       # 12 this week, none before: rise
    add(9, "2026-11-09", "Fraud claims", "Service", 0)       # under the minimum of 10
    add(12, "2026-11-09", "General service", "Other", 0)     # 12 this week against 12 a week before: no rise
    add(48, "2026-10-20", "General service", "Other", 100)
    assert rise_pairs(conn, cfg) == [("Bereavement", "Service")]
