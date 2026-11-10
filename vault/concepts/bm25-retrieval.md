---
tags: [concept]
status: partly unverified
---

# BM25 retrieval

Policy clauses and past notes are found by keyword search: SQLite FTS5 with BM25 ranking. It is exact on clause numbers, lives in one auditable file and needs no extra service. Research note 03 calls it the standard small-corpus pattern and a strong baseline for legal-style retrieval (secondary summary). Dense retrieval can miss exact identifiers such as clause numbers (vendor claim). Vectors are added only if measured retrieval quality requires it.

**Where it comes from:** [[03-on-prem-models-and-retrieval]]

**Used in:** [[search-with-sqlite-fts5]], [[policy-library]], [[case-view]]

**Related:** [[cheapest-tool-per-job]], [[hallucinated-policy]], [[concentration-risk]], [[response-time-limits]]
