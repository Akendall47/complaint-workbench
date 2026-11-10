---
tags: [map]
status: partly unverified
---

# By Ankura solution set

Ankura's AI by Design practice has three solution sets. The mapping below follows [[05-ankura-solution-sets]]. That note says the mapping is inference: Ankura's internal marking is not public. Only the AI by Design page was fetched in full; the rest is from search snippets (UNVERIFIED). Other maps: [[by-brief-requirement]], [[threats-and-controls]], [[evidence-status]]. Start page: [[Home]].

## AI Strategy

Where AI can create value. Brief consideration: business value. Evidence the research note says would satisfy it: value levers, a baseline, a pilot measure, a cost range.

- Decisions: [[use-cheapest-tool-per-job]], [[route-with-small-classifier]], [[search-with-sqlite-fts5]], [[respond-under-100-ms]], [[add-complaint-type-label]], [[deliverables-and-cut-order]]
- Features: [[overview-dashboard]], [[complaint-map]], [[queue-view]], [[complaint-type-filter]]
- Concepts: [[cheapest-tool-per-job]], [[value-case-assumption]], [[token-cost]], [[tf-idf-routing-classifier]], [[bm25-retrieval]], [[concentration-risk]]
- Gap: no baseline or cost range is sourced. See [[value-case-assumption]].

## AI Governance Engineering

Governance as an engineering and user-experience problem, not only policy. Brief consideration: risks, controls and human oversight; also assumptions and limits.

- Decisions: [[person-approves-everything]], [[lock-approve-until-claims-checked]], [[check-citations-word-for-word]], [[mask-before-the-model]], [[limit-what-the-model-can-do]], [[hash-chain-the-audit-log]], [[flags-not-confidence-percentages]], [[use-local-open-model]], [[record-ai-answers-in-advance]], [[verify-before-quoting]], [[synthetic-data-only]], [[stated-non-goals]], [[pipeline-defined-in-configuration]], [[one-configuration-file]]
- Features: [[case-view]], [[per-claim-confirmation]], [[masked-data-with-logged-unmask]], [[audit-log-view]], [[policy-library]], [[settings-view]]
- Concepts: [[governance-built-in]], [[human-approval]], [[citation-check]], [[pii-masking]], [[hash-chained-audit-log]], [[prompt-injection]], [[least-privilege-model]], [[on-premises-model]], [[automated-decision-making]], [[schema-constrained-output]]
- Full list of controls: [[threats-and-controls]]

## Workforce AI Transformation

How roles and handoffs change. Brief consideration: roles and workflows. Evidence the research note says would satisfy it: before-and-after responsibilities, novice and expert impact, a training plan.

- Decisions: [[three-roles-with-switcher]], [[five-case-states]], [[require-reason-to-reject]], [[urgent-by-stated-rules]], [[dashboard-first-left-navigation]], [[minimal-style-effective-wins]]
- Features: [[role-switcher]], [[departments-view]], [[pipeline-view]], [[reject-with-reason]], [[urgent-flag]]
- Concepts: [[novice-uplift-and-deskilling]] (UNVERIFIED), [[returned-case-loop]], [[handover-pack]], [[automation-bias]], [[cognitive-forcing]], [[urgency-rules]]
- Gap: no field study of complaint handlers was found, and no training plan is in the design.

## Tool-agnostic: the AI tools used

- Decision: [[build-with-closed-loop]]
- Concepts: [[closed-build-loop]], [[cross-model-review]]
