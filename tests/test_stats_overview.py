"""Task 9 statistics on a 12-row fixture, hand-computed. Today is Tuesday 2026-11-10; the due-soon edge is 2026-11-17."""
from datetime import date

import pytest

from workbench import stats
from workbench.cases import Actor

ROWS = [  # id, received, state, department, type, deadline, owner, urgent, return_count, handed_over_at, accepted_at
    ("a", "2026-11-09T09:00", "new", "Fraud claims", "Service", "2026-11-20", "H1", 0, 0, None, None),
    ("b", "2026-11-03T10:00", "in_review", "General service", "Service", "2026-11-09", "H1", 1, 0, None, None),
    ("c", "2026-10-31T14:00", "in_review", "General service", "Other", "2026-11-10", "H1", 0, 0, None, None),
    ("d", "2026-10-20T11:00", "handed_over", "Fraud claims", "Service", "2026-11-12", "S1", 0, 0, "2026-10-25", None),
    ("e", "2026-10-20T11:00", "returned", "Fraud claims", "Service", "2026-11-30", "H1", 0, 1, "2026-10-25", None),
    ("f", "2026-10-01T09:00", "accepted", "Fraud claims", "Service", "2026-10-20", "S1", 0, 0, "2026-10-05", "2026-11-05"),
    ("g", "2026-10-01T09:00", "accepted", "Bereavement", "Other", "2026-10-20", "S1", 0, 1, "2026-10-05", "2026-10-15"),
    ("h", "2026-11-10T08:30", "new", "General service", "Other", "2026-12-01", None, 0, 0, None, None),
    ("i", "2026-11-10T16:00", "new", "General service", "Other", "2026-12-01", "H2", 0, 0, None, None),
    ("j", "2026-11-04T08:00", "handed_over", "Bereavement", "Other", "2026-11-13", "S1", 0, 0, "2026-11-06", None),
    ("k", "2026-11-04T08:00", "in_review", "Bereavement", "Other", "2026-11-17", "H2", 1, 0, None, None),
    ("l", "2026-09-15T08:00", "in_review", "General service", "Service", "2026-11-02", "H1", 0, 0, None, None),
]
TODAY = date(2026, 11, 10)


@pytest.fixture
def twelve(conn):
    for r in ROWS:
        conn.execute("INSERT INTO cases(id, received_at, state, department, type, deadline, owner_id, urgent, return_count,"
                     " handed_over_at, accepted_at, version) VALUES (?,?,?,?,?,?,?,?,?,?,?,0)", r)
    return conn


def test_trend_window_is_eight_weeks_of_seven_days(conn):
    from datetime import timedelta
    _add(conn, 1, str(TODAY - timedelta(days=55)), "in")  # last day of the oldest week: counted
    _add(conn, 1, str(TODAY - timedelta(days=56)), "out")  # one day older: not counted
    assert sum(w["new"] for w in stats.trend(conn, TODAY, weeks=8)) == 1


def test_headline(twelve):
    h = stats.headline(twelve, TODAY, set())
    assert (h["open"], h["past_deadline"], h["due_soon"]) == (10, 2, 4)
    assert h["avg_days_open"] == 6.5  # median of 0,0,1,6,6,7,10,21,21,56
    assert h["returned_share"] == 0.4  # 2 of the 5 cases ever handed over came back


def test_headline_empty(conn):
    assert stats.headline(conn, TODAY, set()) == {"open": 0, "due_soon": 0, "past_deadline": 0, "avg_days_open": None, "returned_share": None}


def test_needs_attention_by_role(twelve):
    ids = lambda rows: [r["id"] for r in rows]  # noqa: E731
    assert ids(stats.needs_attention(twelve, Actor("H1", "handler"))) == ["l", "b", "c", "a", "e"]
    assert ids(stats.needs_attention(twelve, Actor("H1", "handler"), limit=2)) == ["l", "b"]
    assert ids(stats.needs_attention(twelve, Actor("T1", "team_lead"), limit=3)) == ["l", "b", "c"]
    twelve.execute("INSERT INTO staff VALUES ('S1','Sam','specialist','Bereavement')")
    assert ids(stats.needs_attention(twelve, Actor("S1", "specialist"))) == ["j"]  # handed over, their department


def test_trend(twelve):
    assert stats.trend(twelve, TODAY, weeks=2) == [{"week": "2026-10-28", "new": 2, "closed": 0}, {"week": "2026-11-04", "new": 5, "closed": 1}]


def test_heatmap(twelve):
    g = stats.heatmap(twelve)
    assert len(g) == 7 and all(len(r) == 11 for r in g) and sum(map(sum, g)) == 12
    assert g[1][0] == 2 and g[1][8] == 1  # Tuesday 08:30 (h and l) and 16:00 (i)


def test_by_department_stage_and_map(twelve):
    assert {r["department"]: r["open"] for r in stats.by_department(twelve)} == {"Fraud claims": 3, "General service": 5, "Bereavement": 2}
    assert dict(stats.by_stage(twelve)) == {"new": 3, "in_review": 4, "handed_over": 2, "returned": 1, "accepted": 2}


def test_team(twelve, cfg):
    for i, (f, t) in enumerate([("new", "in_review"), ("in_review", "handed_over"), ("in_review", "handed_over"), ("handed_over", "returned")]):
        twelve.execute("INSERT INTO events(case_id, at, kind, from_state, to_state, actor_id) VALUES ('a', ?, 'x', ?, ?, 'H1')", (f"2026-11-0{i + 1}", f, t))
    for sid in ("H1", "H2"):
        twelve.execute("INSERT INTO staff VALUES (?, ?, 'handler', NULL)", (sid, sid))
    assert {r["id"]: (r["open"], r["past_deadline"]) for r in stats.team(twelve, TODAY)} == {"H1": (5, 2), "H2": (2, 0)}


def _add(conn, n, day, tag):
    for i in range(n):
        conn.execute("INSERT INTO cases(id, received_at, state, department, type, deadline, version) VALUES (?,?,'new','Bereavement','Service','2027-01-01',0)",
                     (f"{tag}{i}", f"{day}T10:00:00"))


@pytest.mark.parametrize("n_now, n_before, fires", [(10, 20, True), (10, 21, False), (9, 0, False), (20, 40, True), (19, 40, False)])
def test_rises_edge(conn, cfg, n_now, n_before, fires):  # fires at exactly ratio 2.0 with at least 10 cases
    _add(conn, n_now, "2026-11-09", "n")
    _add(conn, n_before, "2026-10-20", "b")
    assert [(r["department"], r["type"]) for r in stats.rises(conn, TODAY, cfg)] == ([("Bereavement", "Service")] if fires else [])


def test_rises_fields(conn, cfg):
    _add(conn, 10, "2026-11-09", "n")
    _add(conn, 20, "2026-10-20", "b")
    r = stats.rises(conn, TODAY, cfg)[0]
    assert (r["this_week"], r["usual"], r["ratio"]) == (10, 5, 2.0)
    assert r["weekly"] == [0, 20, 0, 0, 10]  # oldest first: the four baseline weeks, then this week


def test_shipped_data_has_one_rise(db, cfg):
    import sqlite3
    copy = sqlite3.connect(":memory:")
    db.backup(copy)  # department is filled by the classifier; here the true labels stand in for it
    copy.execute("UPDATE cases SET department = department_true, type = type_true")
    r = stats.rises(copy, TODAY, cfg)
    assert [(x["department"], x["type"], x["this_week"]) for x in r] == [("General service", "Website or app", 46)]


def test_sentence():
    assert stats.sentence("bars", {"title": "Complaints per week", "items": [("1 Nov", 3), ("8 Nov", 5)]}) == \
        "Complaints per week: 1 Nov 3, 8 Nov 5. Highest is 8 Nov with 5."
