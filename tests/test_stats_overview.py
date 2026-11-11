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


def test_heatmap_all_hours_keeps_night_arrivals(twelve):
    twelve.execute("INSERT INTO cases(id, received_at, state, deadline, version) VALUES ('n', '2026-11-09T22:15', 'new', '2027-01-01', 0)")
    assert sum(map(sum, stats.heatmap(twelve))) == 12  # the default 8 to 18 drops it
    g = stats.heatmap(twelve, stats.ALL_HOURS)
    assert all(len(r) == 24 for r in g) and sum(map(sum, g)) == 13 and g[0][22] == 1 and g[1][8] == 2


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


def _event(conn, case, at, to, who="H1"):
    conn.execute("INSERT INTO events(case_id, at, kind, from_state, to_state, actor_id) VALUES (?, ?, 'x', 'a', ?, ?)", (case, at, to, who))


def test_daily_fills_empty_days(twelve):
    assert stats.daily(twelve, TODAY, days=7) == [("2026-11-04", 2), ("2026-11-05", 0), ("2026-11-06", 0), ("2026-11-07", 0),
                                                  ("2026-11-08", 0), ("2026-11-09", 1), ("2026-11-10", 2)]
    assert len(stats.daily(twelve, TODAY)) == 30


def test_snapshot_today_matches_headline(twelve):
    h, s = stats.headline(twelve, TODAY, set()), stats._snapshot(twelve, TODAY, set())
    assert (s["open"], s["past_deadline"], s["due_soon"], s["avg_days_open"]) == (h["open"], h["past_deadline"], h["due_soon"], h["avg_days_open"])


def test_snapshot_a_week_earlier(twelve):
    s = stats._snapshot(twelve, date(2026, 11, 3), set())  # b, c, d, e, l open, and f (accepted 5 Nov); g was accepted 15 Oct
    assert s["open"] == 6 and s["past_deadline"] == 2  # l (2 Nov) and f (20 Oct)
    assert stats._snapshot(twelve, date(2026, 9, 1), set()) is None  # nothing had arrived yet


def test_headline_change(twelve):
    for case, at, to in (("d", "2026-10-25", "handed_over"), ("e", "2026-10-25", "handed_over"), ("e", "2026-11-08", "returned")):
        _event(twelve, case, at, to)
    then, now = stats._snapshot(twelve, date(2026, 11, 3), set()), stats._snapshot(twelve, TODAY, set())
    ch = stats.headline_change(twelve, TODAY, set())
    assert ch["open"] == 10 - 6 and ch["past_deadline"] == 2 - 2 and isinstance(ch["open"], int)
    assert ch["due_soon"] == now["due_soon"] - then["due_soon"] and ch["avg_days_open"] == now["avg_days_open"] - then["avg_days_open"]
    assert ch["returned_share"] == 0.5  # 1 of 2 handovers came back by today, 0 of 2 by 3 Nov


def test_headline_change_is_none_when_it_cannot_be_known(twelve):
    ch = stats.headline_change(twelve, TODAY, set())
    assert ch["returned_share"] is None and ch["open"] is not None  # no events, so no honest returned share at either end
    assert stats.headline_change(twelve, date(2026, 9, 20), set()) == dict.fromkeys(ch)  # 13 Sep: no case had arrived


def test_by_source_and_type(twelve):
    twelve.execute("UPDATE cases SET source = CASE WHEN id IN ('a','b','c') THEN 'phone' WHEN id = 'd' THEN 'letter' ELSE 'email' END")
    twelve.execute("INSERT INTO cases(id, received_at, state, source, deadline, version) VALUES ('z', '2026-11-10T09:00', 'new', 'letter', '2027-01-01', 0)")
    assert stats.by_source(twelve) == [("email", 6), ("phone", 3), ("letter", 2)]  # z has no department and still counts
    assert stats.by_source(twelve, "Fraud claims") == [("email", 1), ("letter", 1), ("phone", 1)]  # ties by key
    assert stats.by_type(twelve) == [("Other", 5), ("Service", 5)]  # z has no type: left out
    assert stats.by_type(twelve, "Fraud claims") == [("Service", 3)]


def test_complaint_map(twelve):
    assert stats.complaint_map(twelve) == [("Fraud claims", "Service", 3), ("General service", "Other", 3),
                                           ("Bereavement", "Other", 2), ("General service", "Service", 2)]


def test_department_table(twelve, cfg):
    rows = stats.department_table(twelve, cfg, TODAY, set(), weeks=2)
    busy = ["General service", "Fraud claims", "Bereavement"]  # most past deadline, then most open; the rest by name
    assert [r["department"] for r in rows] == busy + sorted(d for d in cfg["departments"] if d not in busy)
    assert rows[0] == {"department": "General service", "open": 5, "past": 2, "soon": 1, "weekly": [2, 2]}
    assert rows[1] == {"department": "Fraud claims", "open": 3, "past": 0, "soon": 1, "weekly": [0, 1]}
    assert rows[2] == {"department": "Bereavement", "open": 2, "past": 0, "soon": 2, "weekly": [0, 2]}
    assert all(r["weekly"] == [0, 0] and r["open"] == 0 for r in rows[3:])
    assert len(stats.department_table(twelve, cfg, TODAY, set())[0]["weekly"]) == 8


def test_department_figures(twelve, cfg):
    f = stats.department_figures(twelve, cfg, TODAY, set())
    assert (f["open"], f["past"], f["soon"]) == (10, 2, 4) and f["incomplete_share"] == 2 / 5  # handed over: d, e, f, g, j; sent back: e, g
    assert isinstance(f["top_missing"], str)
    b = stats.department_figures(twelve, cfg, TODAY, set(), "Bereavement")
    assert (b["open"], b["past"], b["soon"], b["incomplete_share"]) == (2, 0, 2, 0.5)  # g sent back, j not
    none = stats.department_figures(twelve, cfg, TODAY, set(), "Data protection")
    assert none == {"open": 0, "past": 0, "soon": 0, "incomplete_share": None, "top_missing": None}


def test_needs_attention_offset_and_count(twelve):
    lead = Actor("T1", "team_lead")
    first, rest = stats.needs_attention(twelve, lead, limit=3), stats.needs_attention(twelve, lead, limit=3, offset=3)
    assert [r["id"] for r in first + rest] == [r["id"] for r in stats.needs_attention(twelve, lead, limit=6)]
    assert stats.attention_count(twelve, lead) == 10 and stats.attention_count(twelve, Actor("H1", "handler")) == 5  # a, b, c, e, l


def test_handovers_offset(twelve):
    twelve.execute("UPDATE cases SET department = 'Bereavement' WHERE id = 'd'")
    rows, n = stats.handovers(twelve, "Bereavement", limit=1)
    more, n2 = stats.handovers(twelve, "Bereavement", limit=1, offset=1)
    assert n == n2 == 2 and [r["id"] for r in rows + more] == ["d", "j"]


def test_team_due_soon_and_closed_week(twelve):
    twelve.execute("INSERT INTO staff VALUES ('H1','Ann','handler',NULL), ('H2','Bo','handler',NULL), ('S1','Sam','specialist','Fraud claims')")
    got = {r["id"]: (r["open"], r["past_deadline"], r["due_soon"], r["closed_week"]) for r in stats.team(twelve, TODAY)}
    assert got == {"H1": (5, 2, 1, 0), "H2": (2, 0, 1, 0), "S1": (2, 0, 2, 1)}  # S1 owns f, accepted 5 Nov; g (15 Oct) is too old
    assert [r["id"] for r in stats.team(twelve, TODAY)] == ["H1", "H2", "S1"]  # ties on open go by id


def test_due_by_day_counts_open_cases_on_each_of_the_next_five_business_days(twelve):
    # Tue 10 (c), Wed 11 (none), Thu 12 (d), Fri 13 (j), Mon 16 (none): b is past deadline and the weekend is skipped
    assert stats.due_by_day(twelve, TODAY, set(), days=5) == [("2026-11-10", 1), ("2026-11-11", 0), ("2026-11-12", 1), ("2026-11-13", 1), ("2026-11-16", 0)]


def test_due_by_day_counts_a_weekend_deadline_on_the_friday_and_adds_up_to_due_soon(twelve):
    twelve.execute("INSERT INTO cases(id, received_at, state, deadline, version) VALUES ('w', '2026-11-01T09:00', 'new', '2026-11-14', 0)")
    got = stats.due_by_day(twelve, TODAY, set())
    assert ("2026-11-13", 2) in got  # j, and w due on Saturday 14
    assert sum(n for _, n in got) == stats.headline(twelve, TODAY, set())["due_soon"]


def test_due_by_day_starts_on_the_next_business_day_at_a_weekend(twelve):
    # Sunday 8 Nov: the first day is Monday 9, when b is due
    assert stats.due_by_day(twelve, date(2026, 11, 8), set(), days=2) == [("2026-11-09", 1), ("2026-11-10", 1)]


def test_draft_checks_sorts_each_claim_into_one_group(conn):
    for i, (inferred, supported) in enumerate([(0, 1), (0, 1), (1, 1), (0, 0), (1, 0)]):
        conn.execute("INSERT INTO claims(case_id, seq, text, quote, inferred, supported, status) VALUES (?,?,?,?,?,?,'draft')",
                     ("a" if i < 3 else "b", i, "t", "q", inferred, supported))
    assert stats.draft_checks(conn) == {"found": 2, "inferred": 1, "missing": 2, "drafts": 2}
