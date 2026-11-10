---
tags: [feature]
status: partly unverified
---

# Masked data with logged unmask

Customer details are masked in the notes on screen, and before any text reaches the model. To see a masked value, the user unmasks it. Unmasking is a logged action and needs a reason. Limitation: the masking patterns are tuned to synthetic data. Unit tests and adversarial cases cover unusual formats.

**Decisions behind it:** [[mask-before-the-model]], [[hash-chain-the-audit-log]], [[synthetic-data-only]]

**Concepts it uses:** [[pii-masking]], [[hash-chained-audit-log]], [[adversarial-test-cases]], [[on-premises-model]]

**Sits in:** [[case-view]]. **Logged in:** [[audit-log-view]]
