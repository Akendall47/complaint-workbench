---
tags: [decision]
status: reasoning
---

# Assign cases without scoring people

**Decision:** Every case has an owner and a Team view shows the load per person. It has no ranking and no speed-per-case figure.

**Who decided:** Owner asked to see who is assigned to what. The limits are my calls.

**Why:** A speed target would reward approving AI drafts without checking them. That is the failure the per-claim check exists to prevent ([[automation-bias]], [[per-claim-confirmation]]).

**How:**
- The Queue has an Owner column and filters for my cases, unassigned and all. A handler can take an unassigned case. A team lead can assign or reassign. Each change is logged.
- Team view: one row per person with open cases, past deadline, due within 5 days, closed this week and returned by specialists. The team lead sees everyone. Others see their own row.
- "Returned by specialists" stays because it measures handover quality, the problem in the brief ([[returned-case-loop]]).
- A department with no specialist keeps the handler as owner after handover.

**Limit:** In a real bank, monitoring staff through this data would need the bank's own data protection and HR review. The deck names this as a workforce risk ([[novice-uplift-and-deskilling]]).

**Trade-off:** Our reasoning: no ranking means less pressure to game the numbers and less to show a manager.

**What would change it:** The bank's own policy on staff monitoring.

**Shows in:** [[queue-view]], [[departments-view]], [[three-roles-with-switcher]], [[five-case-states]]
