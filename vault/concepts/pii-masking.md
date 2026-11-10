---
tags: [concept]
status: partly unverified
---

# PII masking

Customer details are replaced before any text reaches a model, and on screen. The method is known-field replacement plus patterns for account numbers, sort codes, phone numbers, emails and postcodes. It is deterministic and testable. Unmasking is a logged action with a reason. Limitation: the patterns are tuned to synthetic data. OWASP's 2025 list puts sensitive information disclosure second (LLM02) (UNVERIFIED: search summary).

**Where it comes from:** [[02-ai-threats-and-controls]]

**Used in:** [[mask-before-the-model]], [[masked-data-with-logged-unmask]], [[case-view]]

**Related:** [[on-premises-model]], [[adversarial-test-cases]], [[hash-chained-audit-log]], [[synthetic-data]]
