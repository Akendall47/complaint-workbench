---
tags: [feature]
status: reasoning
---

# Reject with reason

Reject needs a written reason. It rejects the AI draft, not the complaint. The draft is discarded, the reason is logged, and the handler completes the summary and pack by hand. The case stays In review. A specialist returning a handover also gives a reason. Research note 07 says requiring a reason is our own design reasoning. A browser test checks that Reject needs a reason.

**Decisions behind it:** [[require-reason-to-reject]], [[person-approves-everything]], [[five-case-states]]

**Concepts it uses:** [[routine-confirmation-dialogs]], [[human-approval]], [[returned-case-loop]], [[hash-chained-audit-log]]

**Sits in:** [[case-view]], [[departments-view]]. **Logged in:** [[audit-log-view]]
