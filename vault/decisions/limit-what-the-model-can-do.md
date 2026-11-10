---
tags: [decision]
status: partly unverified
---

# Limit what the model can do

**Decision:** Notes reach the model as delimited data; the model has no tools and no network access; output must match a schema; links and images are stripped.

**Who decided:** Not tagged in the design document.

**Why:** Complaint text is written by customers and may hide instructions. The aim is to limit the impact.

**Evidence:** [[prompt-injection]], [[least-privilege-model]], [[schema-constrained-output]]; all from [[02-ai-threats-and-controls]] and [[03-on-prem-models-and-retrieval]] (UNVERIFIED: search summaries). Tested with [[adversarial-test-cases]].

**Trade-off:** Our reasoning: a model with no tools cannot look anything up, so search must supply the policy clauses.

**What would change it:** Our reasoning: giving the model tools would need new controls first.

**Shows in:** [[case-view]], [[policy-library]]
