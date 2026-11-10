---
tags: [decision]
status: reasoning
---

# Use the cheapest tool per job

**Decision:** Use the cheapest technique that does each job well; the language model only drafts the summary and suggests handover field values.

**Who decided:** Owner asked for hand-built ML where a language model is not needed. The framing as the central argument is in the design document, not tagged.

**Why:** Plain code is deterministic, testable and free per case. Drafting is the one job that needs language understanding.

**Evidence:** [[cheapest-tool-per-job]]; [[token-cost]] in [[04-token-usage-and-agent-teams]] (one figure marked confirmed, the rest vendor claims). Applying it to this product is our reasoning. It also serves [[governance-built-in]].

**Trade-off:** Several small techniques to build and test in place of one model call. Our reasoning.

**What would change it:** Measurement. Example from the design: vector search is added only if measured retrieval quality requires it.

**Shows in:** [[case-view]], [[queue-view]], [[policy-library]]
