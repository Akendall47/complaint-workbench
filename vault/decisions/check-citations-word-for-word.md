---
tags: [decision]
status: reasoning
---

# Check citations word for word

**Decision:** A claim whose quoted source is not found word for word in the notes is marked "unsupported" and cannot be confirmed.

**Who decided:** Not tagged in the design document.

**Why:** It is a hard check, not a model's opinion. Anti-goal: an AI claim with no matching source passage must never be shown as if it were supported.

**Evidence:** [[citation-check]]. [[03-on-prem-models-and-retrieval]] found no source for the practice, so this is our reasoning. The risk it answers: [[hallucinated-policy]] (UNVERIFIED).

**Trade-off:** Our reasoning: a match shows the quote exists, not that the claim follows from it. The handler can remove or rewrite a claim.

**What would change it:** Our reasoning: a high share of failed claims in the final recording run. That share is reported as a test result.

**Shows in:** [[case-view]], [[per-claim-confirmation]]
