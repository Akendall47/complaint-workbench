---
tags: [decision]
status: partly unverified
---

# Synthetic data only

**Decision:** All data is synthetic, made by a seeded generator; no Kaggle or regulator complaint text is used.

**Who decided:** My call, following the brief.

**Why:** The brief requires fictional or synthetic data. Public complaint datasets contain real people's complaints.

**Evidence:** [[synthetic-data]]; the brief. Proportions are loosely shaped on FCA totals in [[01-complaint-rules]] and described as illustrative.

**Trade-off:** Classifier accuracy will be higher than on real complaints, and masking is tuned to synthetic formats. [[adversarial-test-cases]] are added on purpose.

**What would change it:** Our reasoning: nothing within this task; the brief fixes it.

**Shows in:** [[queue-view]], [[policy-library]], [[overview-dashboard]]
