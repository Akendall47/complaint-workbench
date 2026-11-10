---
tags: [map]
status: partly unverified
---

# By brief requirement

The brief lists five things a submission should consider. Each links the decisions, features and concepts that answer it. Other maps: [[by-ankura-solution-set]], [[threats-and-controls]], [[evidence-status]]. Start page: [[Home]].

## 1. The potential business value

- Decisions: [[use-cheapest-tool-per-job]], [[route-with-small-classifier]], [[search-with-sqlite-fts5]], [[respond-under-100-ms]], [[add-complaint-type-label]], [[dashboard-first-left-navigation]]
- Features: [[overview-dashboard]], [[queue-view]], [[policy-library]], [[complaint-map]], [[complaint-type-filter]]
- Concepts: [[value-case-assumption]], [[cheapest-tool-per-job]], [[handover-pack]], [[glanceable-dashboard]], [[response-time-limits]]
- Honest gap: no cost-per-complaint figure was found. The value case rests on a stated assumption.

## 2. Relevant risks, controls and human oversight

- Decisions: [[person-approves-everything]], [[lock-approve-until-claims-checked]], [[check-citations-word-for-word]], [[mask-before-the-model]], [[limit-what-the-model-can-do]], [[hash-chain-the-audit-log]], [[flags-not-confidence-percentages]], [[require-reason-to-reject]], [[use-local-open-model]]
- Features: [[case-view]], [[per-claim-confirmation]], [[reject-with-reason]], [[masked-data-with-logged-unmask]], [[audit-log-view]]
- Concepts: [[human-approval]], [[citation-check]], [[pii-masking]], [[prompt-injection]], [[automation-bias]], [[cognitive-forcing]], [[hash-chained-audit-log]], [[governance-built-in]]
- Full list: [[threats-and-controls]]

## 3. How people's roles or workflows may change

- Decisions: [[three-roles-with-switcher]], [[five-case-states]], [[urgent-by-stated-rules]], [[pipeline-defined-in-configuration]]
- Features: [[role-switcher]], [[departments-view]], [[pipeline-view]], [[urgent-flag]]
- Concepts: [[returned-case-loop]], [[handover-pack]], [[novice-uplift-and-deskilling]] (UNVERIFIED), [[urgency-rules]], [[vulnerable-customers]] (UNVERIFIED)

## 4. Any assumptions, limitations or trade-offs

- Decisions: [[stated-non-goals]], [[synthetic-data-only]], [[verify-before-quoting]], [[minimal-style-effective-wins]], [[one-configuration-file]], [[deliverables-and-cut-order]]
- Features: [[settings-view]], [[role-switcher]]
- Concepts: [[synthetic-data]], [[complaint-deadlines]] (UNVERIFIED), [[heatmap-caveat]], [[aesthetic-usability-effect]], [[adversarial-test-cases]]
- Every decision note has a trade-off line. What is verified: [[evidence-status]]

## 5. The AI tools used and the candidate's assessment of them

- Decisions: [[build-with-closed-loop]], [[record-ai-answers-in-advance]], [[use-local-open-model]], [[server-rendered-stack]]
- Concepts: [[closed-build-loop]], [[cross-model-review]], [[token-cost]], [[on-premises-model]], [[recorded-ai-output]], [[schema-constrained-output]]
- Research: [[04-token-usage-and-agent-teams]], [[03-on-prem-models-and-retrieval]]

## The scenario's three asks

- Protect customer information: [[pii-masking]], [[on-premises-model]], [[masked-data-with-logged-unmask]]
- Keep decisions reviewable: [[hash-chained-audit-log]], [[citation-check]], [[audit-log-view]]
- How staff and specialists would use it: [[queue-view]], [[case-view]], [[departments-view]]
