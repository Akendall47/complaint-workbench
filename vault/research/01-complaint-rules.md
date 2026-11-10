---
tags: [research, regulation, complaints]
date: 2026-11-10
status: partly unverified
---

# UK complaint-handling rules

Research agent report, 2026-11-10. The FCA Handbook pages could not be fetched, so the core DISP rules below come from memory and must be checked against the primary text before they are quoted. Related: [[02-ai-threats-and-controls]], [[05-ankura-solution-sets]].

## FCA DISP (UNVERIFIED against primary text)

Confirm at https://www.handbook.fca.org.uk/handbook/DISP/1/1.html

- A complaint is any expression of dissatisfaction about the provision of, or failure to provide, a financial service, whether justified or not.
- Summary resolution: close of business on the third business day (DISP 1.5).
- Final response: within 8 weeks (DISP 1.6).
- Payment-services complaints: 15 business days, extendable to 35 (DISP 1.6).
- A final response must accept the complaint, offer redress, or reject it with reasons, and must explain Financial Ombudsman Service (FOS) rights and the 6-month referral window.
- Firms must keep records and carry out root-cause analysis (DISP 1.3).

## Changes in 2026

- Acknowledgements must state that a written response will come within 8 weeks, from 1 June 2026. Source is a member briefing: https://www.abcul.coop/members-briefings/10548/
- A single unified complaints return replaces five existing returns. The FCA will publish firm data above 500 complaints. https://www.fca.org.uk/publications/consultation-papers/ps25-19-improving-complaints-reporting-process
- FOS redress reform (CP26/9) takes effect 1 October 2026. Sources conflict on the detail. https://www.forvismazars.com/uk/en/insights/financial-services-insights/shaping-the-future-of-consumer-redress

## Consumer Duty and vulnerable customers (not researched, UNVERIFIED)

FG21/1 names four vulnerability drivers: health, life events, resilience and capability. Handlers should spot signals, record them and adjust handling. Check https://www.fca.org.uk/publications/finalised-guidance/guidance-firms-fair-treatment-vulnerable-customers

## Handover fields per category

This list is the research agent's own synthesis. It is an assumption of the prototype, not a regulatory list.

Common to all: case ID, customer ID, date received, deadline clocks, complaint wording, outcome wanted, vulnerability flag and adjustments, products involved, actions already taken.

| Category | Extra fields |
|---|---|
| Payment scam (APP fraud) | Payment date, amount, payment type, recipient details, scam type, warning history, vulnerable-customer exception, claim excess, reimbursement clock |
| Financial difficulty | Arrears, income and expenditure, forbearance offered, debt-advice involvement |
| Bereavement | Date of death, who is notifying, proof provided, executor or personal representative |
| Vulnerable customer | Vulnerability type, disclosures made, consent to record |
| Data request (DSAR) | Request date, one-month clock, scope, exemptions considered |
| Mis-selling | Product, sale date, channel, advice record, suitability documents |

Sourced facts on payment scams: maximum reimbursement £85,000 per claim, generally 5 business days to pay or up to 35 if the clock is paused (https://moneytothemasses.com/banking/what-are-the-new-app-fraud-reimbursement-rules). Excess of up to £100 may apply. Regulator page: https://www.psr.org.uk/information-for-consumers/app-fraud-reimbursement-protections/

## Figures for the value case

- FCA H2 2025: about 1.74m complaints (revised 15 May 2026), 55.54% upheld by firms, £236m redress. Banking and credit cards 857,757. https://www.fca.org.uk/data/complaints-data/aggregate-complaints-data-2025-h2
- FOS overall uphold rate 30% in 2025/26. FOS expects 188,000 cases in 2026/27. https://www.financial-ombudsman.org.uk/who-we-are/data-insight/news/financial-ombudsman-received-53600-cases-first-quarter-202627
- FOS case fee rise from £650 to £680 was proposed; adoption not confirmed. https://www.mortgagesolutions.co.uk/mortgage-news/2026/01/13/fos-lays-out-plan-to-up-fees-after-two-year-freeze/
- Cost per complaint: not found. Any figure used is an assumption.

## Data protection

- The Data (Use and Access) Act 2025 replaced Article 22 with Articles 22A to 22D, moving from a prohibition to a safeguards regime, in force 5 February 2026. https://www.traverssmith.com/knowledge/knowledge-container/uks-data-protection-reforms-take-effect-a-new-era-for-automated-decision-making/
- Not researched: special category data, data minimisation, ICO guidance on AI.

## Still to check

Primary DISP text, FG21/1, ICO AI guidance.
