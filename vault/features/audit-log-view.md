---
tags: [feature]
status: reasoning
---

# Audit log view

For the team lead and the reviewer: every action, who took it and when. The role in use is recorded with each action. Entries cover confirmations, edits with the original text, rejections with reasons, routing changes, urgent-flag changes and unmasking. The log is append-only and hash-chained, so a changed entry is detectable. It does not prevent tampering.

**Decisions behind it:** [[hash-chain-the-audit-log]], [[three-roles-with-switcher]], [[require-reason-to-reject]], [[mask-before-the-model]]

**Concepts it uses:** [[hash-chained-audit-log]], [[human-approval]], [[governance-built-in]]

**Fed by:** [[case-view]], [[departments-view]], [[masked-data-with-logged-unmask]], [[role-switcher]]
