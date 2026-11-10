---
tags: [decision]
status: reasoning
---

# Flags, not confidence percentages

**Decision:** Inferred claims carry a "check this" flag; no confidence percentage is shown.

**Who decided:** Not tagged in the design document. It is rule 3 of the agent's own proposed rules in [[06-interface-design]].

**Why:** A bare percentage invites trust the model has not earned. Our reasoning.

**Evidence:** [[check-this-flag]]. [[07-ux-evidence]] says evidence on confidence percentages is not verified: this is our own design reasoning. Related risk: [[automation-bias]]. Typical flagged claim: [[vulnerable-customers]].

**Trade-off:** Our reasoning: the handler learns less about how sure the model is.

**What would change it:** Our reasoning: verified evidence on confidence displays.

**Shows in:** [[case-view]], [[per-claim-confirmation]]
