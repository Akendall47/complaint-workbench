---
tags: [research, verification]
date: 2026-11-10
status: verified
---

# Verification against primary sources

Checked on 2026-11-10. This note overrides any UNVERIFIED mark on the same fact in [[01-complaint-rules]], [[02-ai-threats-and-controls]], [[05-ankura-solution-sets]] and [[07-ux-evidence]]. Rule: [[verify-before-quoting]]. Status map: [[evidence-status]].

The FCA Handbook pages are drawn by script, so a plain fetch returns nothing. They were read in a real browser.

## Verified, page read

| Fact, as it may be stated | Supporting words | Source |
|---|---|---|
| A firm must send a final response by the end of eight weeks after receiving a complaint (DISP 1.6.2R). | "the respondent must, by the end of eight weeks after its receipt of the complaint, send the complainant" | https://handbook.fca.org.uk/handbook/disp1/disp1s6 |
| Payment services and e-money complaints: final response by the end of 15 business days, or in exceptional circumstances a holding response by 15 and a final response by 35 business days (DISP 1.6.2AR). | "send a final response to the complainant by the end of 35 business days after the day on which it received the complaint" | same |
| A firm must send a prompt written acknowledgement (DISP 1.6.1R). | "send the complainant a prompt written acknowledgement" | same |
| Complaints resolved by close of business on the third business day after receipt are exempt from several rules (DISP 1.5; section last updated 1 April 2018). | "resolved by a respondent by close of business on the third business day following the day on which it is received" | https://handbook.fca.org.uk/handbook/disp1/disp1s5 |
| Firms must identify and remedy recurring or systemic problems, including root causes (DISP 1.3.3R). | "analysing the causes of individual complaints so as to identify root causes common to types of complaint" | https://handbook.fca.org.uk/handbook/disp1/disp1s3 |
| FCA guidance FG21/1, "Guidance for firms on the fair treatment of vulnerable customers", first published 23 February 2021. Four areas: health, life events, resilience, capability. | "low resilience to cope with financial or emotional shocks" | https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers |
| FCA 2025 H2 (revised 15 May 2026): 1.74 million complaints received, 55.54% upheld, £236m redress. | "we have updated the H1 2025 and H2 2025 data" | https://www.fca.org.uk/data/complaints-data/aggregate-complaints-data-2025-h2 |
| Financial Ombudsman Service upheld 30% of complaints it resolved in 2025/26. | "we upheld 30% of the complaints we resolved." | https://www.financial-ombudsman.org.uk/data-insight/our-insight/annual-complaints-data-and-insight-2025-26 |
| APP scam reimbursement: up to £85,000, for payments on or after 7 October 2024. | "People will be covered up to £85,000 as standard." | https://www.psr.org.uk/news-and-updates/latest-news/news/groundbreaking-new-protections-for-victims-of-app-scams-start-today/ |
| Data (Use and Access) Act 2025, section 80, replaces Article 22 UK GDPR with Articles 22A to 22D; commenced 5 February 2026. | "For Article 22 of the UK GDPR... substitute" | https://www.legislation.gov.uk/ukpga/2025/18/section/80 |
| OWASP Top 10 for LLM Applications 2025: LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM05 Improper Output Handling, LLM06 Excessive Agency. | "LLM01:2025 Prompt Injection" | https://genai.owasp.org/llm-top-10/ |
| NCSC, 8 December 2025: prompt injection may never be fully mitigated. | "may never be totally mitigated in the way that SQL injection attacks can be" | https://www.ncsc.gov.uk/blog-post/prompt-injection-is-not-sql-injection |
| CVE-2025-32711: command injection in Microsoft 365 Copilot allowing information disclosure. | "Ai command injection in M365 Copilot allows an unauthorized attacker to disclose information over a network." | NVD entry for CVE-2025-32711 |
| Brynjolfsson, Li and Raymond, "Generative AI at Work": about 14% average productivity gain, about 34% for novices. Quarterly Journal of Economics 140(2), 2025. | "rose about 14%... roughly 34%" | https://www.nber.org/papers/w31161 |
| Buçinca, Malaya and Gajos 2021: three cognitive forcing designs (explanation on demand, decide first then update, forced wait) reduced over-reliance compared with simple explanations; 199 participants; the designs that worked best were liked least; larger benefit for people high in Need for Cognition. | "cognitive forcing significantly reduced overreliance compared to the simple explainable AI approaches" | https://ar5iv.labs.arxiv.org/html/2102.09692 |
| Bansal et al. 2021: explanations raised acceptance of the AI's recommendation whether or not it was correct. | "explanations increased the chance that humans will accept the AI's recommendation, regardless of its correctness." | https://ar5iv.labs.arxiv.org/html/2006.14779 |

## Wording to be careful with

- 1.74 million is complaints received, not a general "total". Complaints closed were 1,720,632.
- Per-claim confirmation is our application of the cognitive forcing principle. The paper did not test it.
- "EchoLeak" and "zero-click" come from secondary reports, not from the NVD entry.

## Not verified, so not stated as fact

- The record-keeping period in DISP 1.9. The page was not reached.
- The 2026 changes to DISP (a redress instrument said to take effect 1 June 2026, and Ombudsman changes on 1 October 2026) were seen in search snippets only. The DISP 1.6 text quoted above was read as in force on 10 November 2026.
- Moffatt v Air Canada, 2024 BCCRT 149: the decision itself could not be opened. Secondary summaries say the airline was held liable for its chatbot's wrong information. If used, it is attributed to those summaries.
