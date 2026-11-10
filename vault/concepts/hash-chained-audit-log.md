---
tags: [concept]
status: reasoning
---

# Hash-chained audit log

Every action writes an entry to a log that can only be added to. Each entry stores a hash of the one before, so a changed entry is detectable. The chain detects tampering; it does not prevent it. The role in use is recorded with each action. Research note 02 lists an audit log and a named approver as the control for accountability. The hash chain itself is the design author's choice, with no source: our reasoning.

**Where it comes from:** [[02-ai-threats-and-controls]]; "audit trail" is in Ankura's vocabulary in [[05-ankura-solution-sets]]

**Used in:** [[hash-chain-the-audit-log]], [[audit-log-view]], [[masked-data-with-logged-unmask]]

**Related:** [[human-approval]], [[pii-masking]], [[governance-built-in]], [[returned-case-loop]]
