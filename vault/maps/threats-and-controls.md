---
tags: [map]
status: partly unverified
---

# Threats and controls

Each threat is linked to the control that answers it. The threats come from [[02-ai-threats-and-controls]], which was built from search summaries; the pages were not opened (UNVERIFIED). The controls come from section 10 of the design document. Other maps: [[by-brief-requirement]], [[by-ankura-solution-set]], [[evidence-status]]. Start page: [[Home]].

| Threat | Control | Decision | Where you see it |
|---|---|---|---|
| Instructions hidden in complaint text: [[prompt-injection]] | [[least-privilege-model]], [[schema-constrained-output]], [[adversarial-test-cases]] | [[limit-what-the-model-can-do]] | [[case-view]] |
| Invented facts or citations | [[citation-check]] | [[check-citations-word-for-word]] | [[per-claim-confirmation]] |
| Invented policy: [[hallucinated-policy]] | Clauses come from search, never the model: [[bm25-retrieval]] | [[search-with-sqlite-fts5]] | [[policy-library]] |
| Customer data exposure | [[pii-masking]]; unmasking logged with a reason | [[mask-before-the-model]] | [[masked-data-with-logged-unmask]] |
| Customer data sent to a third party | [[on-premises-model]], [[pii-masking]] | [[use-local-open-model]] | Whole product |
| Rubber-stamping: [[automation-bias]] | [[cognitive-forcing]], [[check-this-flag]], reasons and edits logged | [[lock-approve-until-claims-checked]], [[flags-not-confidence-percentages]], [[require-reason-to-reject]] | [[per-claim-confirmation]], [[reject-with-reason]] |
| The AI appears to decide: [[automated-decision-making]] | [[human-approval]] | [[person-approves-everything]], [[stated-non-goals]] | [[case-view]] |
| Tampering with the record | [[hash-chained-audit-log]] | [[hash-chain-the-audit-log]] | [[audit-log-view]] |
| Third-party dependence: [[concentration-risk]] | Local open model, one SQLite file, no external requests: [[server-rendered-fragments]] | [[use-local-open-model]], [[server-rendered-stack]] | Whole product |
| Web basics | Output escaping, parameterised queries, input validation | [[server-rendered-stack]] | Every form |
| Urgent or vulnerable case missed: [[vulnerable-customers]] | [[urgency-rules]] with reasons shown | [[urgent-by-stated-rules]] | [[urgent-flag]] |
| Incomplete handover | [[handover-pack]], [[returned-case-loop]] | [[five-case-states]] | [[departments-view]] |
| Unverified figure presented as fact | Check against a primary source | [[verify-before-quoting]] | [[evidence-status]] |

The last three rows are threats named by the design document or the brief, not by the research note.

## Stated limits of the controls

- No real authentication or access control: [[role-switcher]].
- Masking patterns are tuned to synthetic data.
- The hash chain detects tampering but does not prevent it.
- Per-claim confirmation is an application of a principle, not a tested design.
- Prompt-injection classifiers are not relied on.

## Threats in the research with no stated control in the design

- Poisoned policy index. The research note proposes a read-only index with provenance shown for each clause. The design document does not state this.
- Model drift. The research note proposes a fixed evaluation set, rerun on any model change. The design document fixes the prompt version and seed for the recordings ([[recorded-ai-output]]) but does not state a rerun rule.
