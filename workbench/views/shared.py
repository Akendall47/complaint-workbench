"""Names and helpers every page uses: the demo roles, stage names, who is looking, and the deadline pills."""
from urllib.parse import urlencode

from .. import audit
from ..cases import Actor
from ..stats import rise_pairs

DEMO = {"handler": "H1", "specialist": "S1", "team_lead": "T1"}
ROLE_NAME = {"handler": "Handler", "specialist": "Specialist", "team_lead": "Team lead"}
HOME = {"handler": "/queue", "specialist": "/departments", "team_lead": "/"}
STATE_NAME = {"new": "New", "in_review": "In review", "handed_over": "Handed over", "returned": "Returned", "accepted": "Accepted"}


def current_actor(request) -> Actor:
    role, sid = request.cookies.get("role"), request.cookies.get("staff_id")
    if role in DEMO and sid == DEMO[role]:
        return Actor(sid, role)
    return Actor("H1", "handler")


def strip(conn, cfg, edge: str) -> dict:
    limit = cfg["urgent"]["deadline_within_business_days"]
    one = lambda q, *a: conn.execute(q, a).fetchone()[0]  # noqa: E731
    open_ = "state != 'accepted' AND "
    rises = rise_pairs(conn, cfg)
    return {"past": one(f"SELECT COUNT(*) FROM cases WHERE {open_}deadline < ?", cfg["today"]),
            "soon": one(f"SELECT COUNT(*) FROM cases WHERE {open_}deadline >= ? AND deadline <= ?", cfg["today"], edge),
            "urgent": one(f"SELECT COUNT(*) FROM cases WHERE {open_}urgent = 1"),
            "rises": len(rises), "rise_query": urlencode({"owner": "all", "department": rises[0][0], "type": rises[0][1]}) if rises else "",
            "limit": limit, "updated": audit.now()[11:16]}
