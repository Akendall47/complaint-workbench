---
tags: [decision]
status: partly unverified
---

# Search with SQLite FTS5

**Decision:** Find policy clauses and past notes with SQLite FTS5 and BM25 ranking; no vector search unless measurement requires it.

**Who decided:** Not tagged in the design document.

**Why:** Exact on clause numbers, one auditable file, no extra service. Policy clauses come from search, never from the model.

**Evidence:** [[bm25-retrieval]] in [[03-on-prem-models-and-retrieval]] (secondary and vendor sources, UNVERIFIED); [[hallucinated-policy]]; [[concentration-risk]].

**Trade-off:** Our reasoning: keyword search can miss a clause worded differently from the complaint. Test: a small labelled set, reporting how often the right clause is in the top five.

**What would change it:** Measured retrieval quality that requires vectors (stated in the design).

**Shows in:** [[policy-library]], [[case-view]]
