---
tags: [decision]
status: partly unverified
---

# Mask before the model

**Decision:** Mask customer details with deterministic rules before any text reaches a model and on screen; unmasking is a logged action with a reason.

**Who decided:** Not tagged in the design document.

**Why:** The brief requires the approach to protect customer information. Rules are deterministic and testable.

**Evidence:** [[pii-masking]]; the threat table in [[02-ai-threats-and-controls]] (search summaries, UNVERIFIED); [[adversarial-test-cases]] for unusual formats.

**Trade-off:** The patterns are tuned to synthetic data. This is a stated limitation.

**What would change it:** Our reasoning: real data formats that the patterns miss.

**Shows in:** [[masked-data-with-logged-unmask]], [[case-view]], [[audit-log-view]]
