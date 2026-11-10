---
tags: [feature]
status: partly unverified
---

# Policy library

For everyone: search and read the bank's policy clauses. The library is about 40 fictional clauses written for this bank, each with a clause number. Clauses listed in the Case view open here. Clauses come from search, never from the model. Research note 02 proposes a read-only index with provenance shown for each clause; the design document does not state that control, so it is not claimed here.

**Decisions behind it:** [[search-with-sqlite-fts5]], [[synthetic-data-only]], [[limit-what-the-model-can-do]], [[server-rendered-stack]]

**Concepts it uses:** [[bm25-retrieval]], [[hallucinated-policy]] (UNVERIFIED), [[synthetic-data]]

**Reached from:** [[case-view]]. Research: [[02-ai-threats-and-controls]]
