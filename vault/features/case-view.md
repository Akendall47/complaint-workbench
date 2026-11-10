---
tags: [feature]
status: partly unverified
---

# Case view

Where the handler does the work. Notes are shown masked. The summary appears as separate claims, labelled as an AI draft, each with a numbered citation that highlights its source passage. Unsupported claims cannot be confirmed. Inferred claims carry a "check this" flag. Matching policy clauses are listed with clause numbers. The handover pack names missing fields. The predicted department and the words that drove it sit at the top. Approve or reject ends the step. Every step writes an audit entry.

**Decisions behind it:** [[person-approves-everything]], [[check-citations-word-for-word]], [[lock-approve-until-claims-checked]], [[flags-not-confidence-percentages]], [[mask-before-the-model]], [[limit-what-the-model-can-do]], [[record-ai-answers-in-advance]]

**Concepts it uses:** [[citation-check]], [[human-approval]], [[cognitive-forcing]] (UNVERIFIED), [[pii-masking]], [[handover-pack]], [[bm25-retrieval]], [[check-this-flag]]

**Controls inside it:** [[per-claim-confirmation]], [[reject-with-reason]], [[masked-data-with-logged-unmask]], [[urgent-flag]]
