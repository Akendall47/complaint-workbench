---
tags: [map]
status: partly unverified
---

# Evidence status

What is verified, what is not, and what is our own reasoning. "Verified" means a research note says the source was read in full. Quotes came through a page-extraction tool, so the wording is re-checked at the source before it is quoted. Rule: [[verify-before-quoting]]. Other maps: [[by-brief-requirement]], [[by-ankura-solution-set]], [[threats-and-controls]]. Start page: [[Home]].

## 1. Verified from a source read in full

- NN/g on dashboards and chart types: [[glanceable-dashboard]], [[bars-not-pies]]
- NN/g on vertical navigation, including its cost: [[left-navigation]]
- NN/g on removing nonessential elements: [[glanceable-dashboard]]
- NN/g on response times; web.dev Core Web Vitals: [[response-time-limits]]
- NN/g on confirmation dialogs: [[routine-confirmation-dialogs]]
- NN/g on data tables: used in [[queue-view]]
- WCAG use of colour, contrast and target size; GOV.UK tag and error summary: [[colour-not-alone]], [[accessibility-baseline]]
- htmx: [[server-rendered-fragments]]
- Ankura's AI by Design page: [[governance-built-in]]
- The brief itself: synthetic data only, in [[synthetic-data]]

Sources: [[06-interface-design]], [[07-ux-evidence]], [[05-ankura-solution-sets]].

## 2. Unverified

Marked UNVERIFIED in the research:

- FCA DISP rules, from memory: [[complaint-deadlines]], [[summary-resolution]], [[final-response]]; also the record-keeping and root-cause duty (DISP 1.3). Source note: [[01-complaint-rules]]
- FG21/1, not researched: [[vulnerable-customers]]
- Everything in [[02-ai-threats-and-controls]] (search summaries, pages not opened): [[prompt-injection]], [[least-privilege-model]], [[hallucinated-policy]], [[human-approval]], [[automated-decision-making]], the OWASP ranking in [[pii-masking]]
- Named as not verified in note 02: PRA SS1/23, DORA, ISO/IEC 42001, NIST AI RMF, MITRE ATLAS, the content of the OWASP 2026 list, and whether complaint triage is high-risk under the EU AI Act
- Snippet or abstract only: [[automation-bias]], [[cognitive-forcing]], Google PAIR in [[check-this-flag]]
- Summary page only: Guidelines for Human-AI Interaction, G9 "Support efficient correction"
- Not marked as read: [[aesthetic-usability-effect]], the quote in [[heatmap-caveat]], the expandable-rows remark
- Search snippets in note 05: [[novice-uplift-and-deskilling]], Ankura's insight articles and related work
- Listed in note 07 as not verified: Stephen Few, Tufte, Shneiderman, Cleveland and McGill full text, the Doherty threshold paper; sparklines, previous-period comparison, cards, whitespace, density; colour-blindness prevalence

Sourced, but the research note does not say the page was read in full:

- 2026 rule changes, FCA and FOS figures, payment-scam figures, the Data (Use and Access) Act: [[value-case-assumption]], [[automated-decision-making]]
- [[03-on-prem-models-and-retrieval]] (much from blogs; some marked primary): [[on-premises-model]], [[concentration-risk]], [[bm25-retrieval]], [[schema-constrained-output]]
- [[04-token-usage-and-agent-teams]] (mostly vendor claims; Anthropic's figures marked confirmed): [[token-cost]], [[cross-model-review]]

Looked for and not found:

- A cost per complaint. A bank or regulator quote on cost predictability or auditability. A field study of complaint handlers. UK complaints work by Ankura. Evidence for Obsidian vaults as agent memory. A source for quote-then-answer with a verbatim check.

## 3. Our own reasoning, with no source

- The handover field list: [[handover-pack]]
- The eight proposed interface rules in note 06, including [[check-this-flag]] and a reason on rejection: [[require-reason-to-reject]]
- Per-claim confirmation as a use of cognitive forcing: [[lock-approve-until-claims-checked]]
- [[citation-check]], [[recorded-ai-output]], [[hash-chained-audit-log]] (the hash chain)
- [[tf-idf-routing-classifier]], [[cheapest-tool-per-job]] as a product principle
- [[urgency-rules]], [[complaint-type]], [[band-flow-diagram]], [[returned-case-loop]]
- [[closed-build-loop]], [[adversarial-test-cases]]
- The mapping of the five considerations to solution sets: [[by-ankura-solution-set]]
- The choice of control for each threat: [[threats-and-controls]]
- Every "trade-off" or "what would change it" line marked "our reasoning" in the decision notes
