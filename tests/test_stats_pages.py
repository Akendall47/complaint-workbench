"""Statistics behind the one-window pages, on small hand-computed fixtures. Each builder adds tests at the end."""
from workbench import stats
from tests.test_stats_overview import TODAY, twelve  # noqa: F401  (twelve is a fixture)


# ---- Departments, Team, Pipeline ----
def test_handovers_for_every_department_carry_the_handover_fields(twelve):  # noqa: F811
    rows, n = stats.handovers(twelve, "")
    assert n == 2 and [(r["id"], r["department"]) for r in rows] == [("d", "Fraud claims"), ("j", "Bereavement")]
    assert "handover_json" in rows[0]


def test_department_figures_narrow_by_type(twelve, cfg):  # noqa: F811
    f = stats.department_figures(twelve, cfg, TODAY, set(), "", 5, type_="Service")
    assert (f["open"], f["past"], f["soon"]) == (5, 2, 1)  # a, b, d, e, l; b and l late; d due on the 12th
    assert stats.department_figures(twelve, cfg, TODAY, set(), "Fraud claims", 5, source="letter")["open"] == 0


def test_team_figures(twelve):  # noqa: F811
    assert stats.team_figures(twelve, TODAY, set()) == {"open": 10, "unassigned": 1, "past": 2, "soon": 4, "closed_week": 1}  # h has no owner; f accepted 5 Nov


def test_unassigned_cases(twelve):  # noqa: F811
    assert [r["id"] for r in stats.unassigned_cases(twelve)] == ["h"]
    assert stats.unassigned_cases(twelve, offset=1) == []


def test_returned_by_handler_follows_each_handover_to_the_next_move(conn):
    moves = [("x", "new", "system"), ("x", "in_review", "H1"), ("x", "handed_over", "H1"), ("x", "returned", "S1"), ("x", "in_review", "H1"),
             ("x", "handed_over", "H1"), ("x", "accepted", "S1"), ("y", "new", "system"), ("y", "in_review", "H2"), ("y", "handed_over", "H2")]
    prev = {}
    for i, (case, to, actor) in enumerate(moves):
        conn.execute("INSERT INTO events(case_id, at, kind, from_state, to_state, actor_id) VALUES (?,?,?,?,?,?)",
                     (case, f"2026-11-0{1 + i // 4}T{10 + i:02d}:00", to, prev.get(case), to, actor))
        prev[case] = to
    assert stats.returned_by_handler(conn) == {"H1": (2, 1), "H2": (1, 0)}
