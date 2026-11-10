---
tags: [decision]
status: reasoning
---

# Hash-chain the audit log

**Decision:** The audit log is append-only and each entry stores a hash of the previous one.

**Who decided:** My call.

**Why:** A changed entry becomes detectable. Every step in the case flow writes an entry, with the role that took it.

**Evidence:** [[hash-chained-audit-log]]; accountability row in [[02-ai-threats-and-controls]]; [[governance-built-in]]. The hash chain itself has no source: our reasoning.

**Trade-off:** It detects tampering but does not prevent it. There is no real authentication, so the "who" is a role from the [[role-switcher]].

**What would change it:** Our reasoning: a production system would need access control as well.

**Shows in:** [[audit-log-view]], [[masked-data-with-logged-unmask]]
