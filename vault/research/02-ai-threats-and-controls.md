---
tags: [research, security, governance]
date: 2026-11-10
status: partly unverified
---

# AI threats and controls in banking, 2026-27

Research agent report, 2026-11-10. Built from search summaries; pages were not opened. Not verified: PRA SS1/23, DORA, ISO/IEC 42001, NIST AI RMF, MITRE ATLAS, the content of the OWASP 2026 list, and whether complaint triage is high-risk under the EU AI Act. Related: [[01-complaint-rules]], [[03-on-prem-models-and-retrieval]], [[06-interface-design]].

## Threats

- OWASP LLM Top 10 (2025): prompt injection is first (LLM01), sensitive information disclosure second (LLM02). Vector and embedding weaknesses (LLM08) cover retrieval poisoning. https://www.hackerone.com/ai/owasp-top-10-llms-2025
- A 2026 edition was published on 3 August 2026; its changes were not checked. https://labs.cloudsecurityalliance.org/research/csa-research-note-owasp-genai-top10-2026-agent-control-stand/
- OWASP Top 10 for Agentic Applications, 9 December 2025. https://genai.owasp.org/resource/2025-12-09/owasp-top-10-for-agentic-applications-for-2026
- NCSC, December 2025: language models do not separate instructions from data, so prompt injection may never be fully mitigated. Limit impact with least privilege, marking data separately, and monitoring. https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection
- EchoLeak (CVE-2025-32711, CVSS 9.3): a crafted email caused zero-click data exfiltration from M365 Copilot. This matches the threat of instructions hidden in customer-written complaint text. https://thehackernews.com/2025/06/zero-click-ai-vulnerability-exposes.html
- Moffatt v Air Canada (2024): a chatbot invented a bereavement policy and the airline was held liable. This is the precedent for hallucinated policy. https://www.cxtoday.com/contact-center/court-orders-air-canada-to-pay-out-for-chatbots-bad-advice/

## Threat-to-control table

| Threat | Control | Shown in prototype? |
|---|---|---|
| Hidden instructions in complaint text | Case text passed as delimited data, model has no tools, injection test cases | yes |
| Data leaving through model output | Strip URLs and images from output, validate against a schema | yes |
| Poisoned policy index | Read-only index, provenance shown for each clause | yes |
| Invented citations | Every claim must match a source passage, otherwise flagged | yes |
| Customer data sent to a third party | Mask before the model; local model | yes |
| Reviewer over-trust | Source shown beside each claim, per-claim confirmation, overrides logged | partly |
| Model drift | Fixed evaluation set, rerun on any model change | yes |
| Accountability | Audit log, named approver | yes |

Prompt-injection classifiers are not relied on: EchoLeak bypassed Microsoft's own classifier.

## Regulation

- FCA Mills Review, 6 July 2026: advice, not policy. Recommends stronger evidencing of outcomes and live monitoring. https://www.fca.org.uk/publications/calls-input/review-long-term-impact-ai-retail-financial-services-mills-review
- FCA AI Live Testing, second cohort, report due Q1 2027. https://www.fca.org.uk/news/press-releases/fca-announces-second-cohort-ai-live-testing
- Bank of England Financial Policy Committee, 2026: no systemic AI risk yet, work requested on agentic AI. https://www.bankofengland.co.uk/financial-policy-committee-record/2026/april-2026
- EU AI Act: after the Digital Omnibus, Annex III high-risk duties apply from 2 December 2027. https://secureprivacy.ai/blog/eu-ai-act-digital-omnibus-the-new-high-risk-ai-deadlines-after-council-approval

## Human oversight

- ICO draft guidance on automated decision-making, 31 March 2026: human involvement must be active, not tokenistic, with authority to override. https://www.freeths.co.uk/insights-events/legal-articles/2026/ico-consults-on-updated-automated-decision-making-and-profiling-guidance/
- Design implication (inference): show source passages beside each claim, and log edits and rejections.
