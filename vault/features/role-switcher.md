---
tags: [feature]
status: reasoning
---

# Role switcher

A control in the header that chooses the role: handler, specialist or team lead. It stands in for login. The role is recorded in the audit log with each action. Limitation, stated in the design: there is no real authentication or access control.

**Decisions behind it:** [[three-roles-with-switcher]], [[stated-non-goals]], [[hash-chain-the-audit-log]]

**Concepts it uses:** [[hash-chained-audit-log]], [[human-approval]], [[novice-uplift-and-deskilling]] (UNVERIFIED)

**Changes what you see in:** [[queue-view]], [[departments-view]], [[overview-dashboard]], [[audit-log-view]]
