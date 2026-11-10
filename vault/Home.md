# Complaint Workbench knowledge base

Open this folder as a vault in Obsidian. Notes link to each other, so the graph view shows how the research, decisions and build fit together.

## The brief

Ankura AI by Design internship build task, Scenario 1: a fictional bank with a growing complaints backlog. Staff lose time finding information across case notes and policy documents, and specialist teams receive incomplete handovers. Deadline: Wednesday 11 November 2026, 5:30pm GMT.

## Research

- [[01-complaint-rules]]
- [[02-ai-threats-and-controls]]
- [[03-on-prem-models-and-retrieval]]
- [[04-token-usage-and-agent-teams]]
- [[05-ankura-solution-sets]]
- [[06-interface-design]]
- [[07-ux-evidence]]
- [[08-verification]]
- [[09-how-bank-complaint-systems-work]]

Each note states what was verified and what was not. Anything marked UNVERIFIED is checked against a primary source before it appears in the deck or the report.

## Decisions so far

- The product uses AI to find, summarise and draft. A person approves everything.
- AI answers for the synthetic cases are recorded in advance from an open model running locally, so a reviewer needs no API key.
- Deliverables: a working prototype, a five-slide deck, a LaTeX technical sheet as an optional appendix, and this vault.

## Maps

Four ways into the same notes.

- [[by-brief-requirement]]: the brief's five considerations
- [[by-ankura-solution-set]]: AI Strategy, Governance Engineering, Workforce AI Transformation
- [[threats-and-controls]]: each threat and the control that answers it
- [[evidence-status]]: verified, unverified, and our own reasoning

## Decisions (folder `decisions/`)

One note per design decision: who made it, why, the evidence, the cost, and what would change it.

[[person-approves-everything]] · [[use-cheapest-tool-per-job]] · [[route-with-small-classifier]] · [[search-with-sqlite-fts5]] · [[mask-before-the-model]] · [[check-citations-word-for-word]] · [[limit-what-the-model-can-do]] · [[record-ai-answers-in-advance]] · [[use-local-open-model]] · [[synthetic-data-only]] · [[hash-chain-the-audit-log]] · [[lock-approve-until-claims-checked]] · [[flags-not-confidence-percentages]] · [[require-reason-to-reject]] · [[dashboard-first-left-navigation]] · [[minimal-style-effective-wins]] · [[three-roles-with-switcher]] · [[five-case-states]] · [[add-complaint-type-label]] · [[urgent-by-stated-rules]] · [[pipeline-defined-in-configuration]] · [[one-configuration-file]] · [[respond-under-100-ms]] · [[server-rendered-stack]] · [[build-with-closed-loop]] · [[stated-non-goals]] · [[verify-before-quoting]] · [[deliverables-and-cut-order]] · [[guide-first-time-users]] · [[place-by-cost-of-missing-it]] · [[show-where-data-comes-from]] · [[alert-on-unusual-rise]] · [[prove-robustness-with-a-test-bench]] · [[assign-cases-without-scoring-people]]

## Features (folder `features/`)

One note per view or control in the product.

[[overview-dashboard]] · [[complaint-map]] · [[departments-view]] · [[queue-view]] · [[case-view]] · [[pipeline-view]] · [[policy-library]] · [[audit-log-view]] · [[settings-view]] · [[role-switcher]] · [[per-claim-confirmation]] · [[reject-with-reason]] · [[urgent-flag]] · [[complaint-type-filter]] · [[masked-data-with-logged-unmask]]

## Concepts (folder `concepts/`)

One short note per idea in the research or design. Each has a status in its frontmatter: verified, partly unverified, or reasoning.

[[prompt-injection]] · [[automation-bias]] · [[cognitive-forcing]] · [[citation-check]] · [[human-approval]] · [[hash-chained-audit-log]] · [[pii-masking]] · [[on-premises-model]] · [[concentration-risk]] · [[bm25-retrieval]] · [[tf-idf-routing-classifier]] · [[cheapest-tool-per-job]] · [[recorded-ai-output]] · [[schema-constrained-output]] · [[complaint-deadlines]] · [[summary-resolution]] · [[final-response]] · [[vulnerable-customers]] · [[urgency-rules]] · [[complaint-type]] · [[band-flow-diagram]] · [[returned-case-loop]] · [[handover-pack]] · [[token-cost]] · [[cross-model-review]] · [[closed-build-loop]] · [[glanceable-dashboard]] · [[colour-not-alone]] · [[response-time-limits]] · [[aesthetic-usability-effect]] · [[synthetic-data]] · [[left-navigation]] · [[bars-not-pies]] · [[heatmap-caveat]] · [[check-this-flag]] · [[least-privilege-model]] · [[hallucinated-policy]] · [[automated-decision-making]] · [[novice-uplift-and-deskilling]] · [[governance-built-in]] · [[routine-confirmation-dialogs]] · [[accessibility-baseline]] · [[server-rendered-fragments]] · [[value-case-assumption]] · [[adversarial-test-cases]]
