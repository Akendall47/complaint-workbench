---
tags: [decision]
status: reasoning
---

# Require a reason to reject

**Decision:** Rejecting the AI draft needs a written reason, and so does a specialist returning a handover.

**Who decided:** Not tagged in the design document. The detail of what Reject means is my call.

**Why:** Reject discards the AI draft, not the complaint. The reason is logged and the handler finishes the summary and pack by hand.

**Evidence:** [[07-ux-evidence]] says requiring a reason for rejection is our own design reasoning. It also recommends logged reasons in place of warnings: [[routine-confirmation-dialogs]]. Reasons feed the [[returned-case-loop]] and the [[hash-chained-audit-log]].

**Trade-off:** Our reasoning: extra typing at a busy moment.

**What would change it:** Our reasoning: reasons that turn out empty or copied.

**Shows in:** [[reject-with-reason]], [[departments-view]], [[audit-log-view]]
