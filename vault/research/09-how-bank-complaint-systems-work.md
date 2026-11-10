---
tags: [research, practice, software, complaints]
date: 2026-11-10
status: partly verified
---

# How bank complaint systems work in practice

Checked 2026-11-10. Rules and deadlines are in [[01-complaint-rules]] and [[08-verification]]; not repeated here. Related: [[02-ai-threats-and-controls]], [[05-ankura-solution-sets]], [[06-interface-design]], [[07-ux-evidence]].

## What matters for the prototype

1. Two-tier shape is real: a front line that tries to fix at first contact, and a specialist team that investigates the rest. Triage is the handover point.
2. Complaints are logged badly in real firms. The FCA says complaints are not "identified and recorded consistently". Logging and category fields matter.
3. Root cause is the weak spot. Firms do not always record it. Make it a required field at closure.
4. Handover fails by default-passing ("automatically passing it elsewhere") and by missing feedback. A checklist with named missing fields fits.
5. Vendors sell case record, templates, workflow, reporting and AI summaries. Deadline timers are not clearly advertised by name, so show them.
6. FCA good practice: AI supports people; reviewers sometimes see cases without the AI outcome. Poor practice: reviewers "increasingly accepted" AI output. Claim-by-claim checking is defensible.
7. FCA wants audit records of prompts, outputs, model versions and escalation decisions. An audit log is real practice.
8. No source gave cases-per-day targets. Do not invent any in the demo.

## Workflow and roles

| Step | What sources say | Who | Evidence |
|---|---|---|---|
| Channels in | Not found in a primary source. Treated as assumption. | n/a | Not verified |
| Logging | Weak in practice: "Complaints aren't identified and recorded consistently". | Front line | Page read (FCA review) |
| First-line fix | New first-line team set up to "resolve simple complaints quickly and triage more complex complaints". | First line | Page read (PA Consulting) |
| Triage | Harder cases go to "second line complaints teams". | Triage / team lead | Page read (PA) |
| Investigation | Branch complaints supported by a central officer: "Supports branches to investigate and respond". | Complaints officer | Page read (Handelsbanken advert) |
| Final response | Content rules from the Ombudsman: summarise, accept or reject with reasons, six-month right to refer, leaflet. | Handler | Page read (FOS) |
| Ombudsman referral | "Liaises with the FOS, reviewing requests and decisions and referring them to internal stakeholders". | Complaints officer | Page read (Handelsbanken) |
| Root cause and MI | "identifying the root causes for complaints through the production of management information and analysis". | Complaints officer / analyst | Page read (Handelsbanken) |

Team shape, where a source says:

- Lloyds Banking Group: frontline staff handle complaints and a specialist team exists. "empower all 70,000 of its frontline staff to deal with complaints". Vendor case study (Equiniti), page read.
- Same source, vendor claim: "resolve 90 per cent of customer complaints at the first point of contact". PA Consulting (client examples, not a bank named) reports first-line models cutting backlog 33% and resolution times 30%. Consultancy claims, page read.
- Root cause ownership: "it is the wider business that really should be addressing and resolving the underlying root cause". Vendor blog (Aptean), page read.
- QA checker and team leader roles: no primary source found. Not verified.
- Job adverts seen in search results only (snippet only): Chetwood Bank, Allica Bank, Lloyds Dundee (pay band), Handelsbanken (Complaints Officer). None gave daily case volumes.

## Software in use

All rows are vendor claims unless marked. Pages read unless marked.

| Product | What it advertises | URL |
|---|---|---|
| Aptean Respond | "full visibility and traceability for each case"; "pre-configured templates designed to comply with the latest Financial Conduct Authority (FCA) regulations"; "one-click reporting"; AI "helps identify customers who may be vulnerable"; Case Lookout uses AI on past cases for suggestions. Deadline tracking not named; timelines handled by "automated workflows". | https://www.aptean.com/en-GB/industries/financial-services/capability/regulatory-compliance |
| Salesforce (Einstein) | "Complaint Summary" AI summary of a case's related data (listed GA Oct 2024); AI autofill of titles "Coming soon". Page disclaims availability. Handelsbanken advert wants Salesforce experience (page read). | https://www.salesforce.com/uk/artificial-intelligence/use-cases/financial-services/complaints-management/ |
| Equiniti platform at Lloyds | One web platform replacing "30+" legacy systems; integrates with the bank's retail platform; MI for root cause. | https://equinitidotcom-appservice.azurewebsites.net/uk/news-and-views/lbg-case-study |
| Pega Smart Dispute | GenAI summaries of claims and dispute histories. This is payment disputes, not general complaints. Snippet only. | via search: businesswire.com/news/home/20241211846627/en |
| Huntswood, NICE, ServiceNow, Workpro | Not fetched. Huntswood is a consultancy and managed service, named by Aptean as a partner (snippet only). | Not verified |

## Problems regulators found

| Problem | Source and quote | Evidence |
|---|---|---|
| Poor recording | "Weaknesses and failures in recording complaints may result in poor customer experiences" | Page read: https://www.fca.org.uk/publications/multi-firm-reviews/complaints-handling-review-findings/printable/print |
| Root cause not captured or used | MI often focuses on operational data, not "root causes, preventive actions". Root causes "not always captured". | Same page, page read (my paraphrase of the first) |
| Vulnerability | One firm "didn't adequately consider the impact" on a financially vulnerable customer. | Same page, page read |
| Tick-box handling and inconsistent outcomes | Firms must "assess complaints fairly, consistently and promptly". Redress and distress payments varied (TR14/18). | Same page; https://www.fca.org.uk/publications/thematic-reviews/tr14-18-complaint-handling/printable/print, page read |
| Ombudsman lessons ignored | Some firms are not applying Ombudsman determinations to their procedures. | FCA review page, page read |
| Weak front line | FSA 2010: front-line handling often poor, from lack of training, policies and guidance. | Snippet only (search summary; PDF unreadable) |
| Repeat contact | No source found. | Not verified |

The FCA review covers about 40 firms across sectors, not only banks. Date is December 2024 per search summary (snippet only). TR14/18 is marked historical by the FCA, updated August 2025.

## Handover

- Sources describe where it fails, not a template. Aptean blog (vendor): staff do not know when to resolve, lack advice, "automatically passing it elsewhere", and get no feedback on outcomes.
- PA Consulting: handover is the triage step; each step should add value.
- A named list of required handover fields from a regulator or bank: not found. The checklist in the prototype is our design, not a copied practice.

## AI in complaints today

| Fact | Source | Evidence |
|---|---|---|
| FCA good and poor practice on AI, published 19 Oct 2026. A firm used an LLM to "develop or refine letters responding to consumer queries and complaints"; case officers reviewed and sent each one; consumers tested it and found it clearer. | https://www.fca.org.uk/publications/good-poor-practice/ai-financial-services/printable/print | Page read |
| Good practice: "Firms kept records of consumer prompts, outputs, model versions, applied filters and escalation decisions." | Same | Page read |
| Good practice: "AI systems to support rather than replace people's judgement"; case study N reviewers did not see the AI's proposed outcome. | Same | Page read |
| Poor practice: reviewers "increasingly accepted AI-generated recommendations without sufficient scrutiny"; review risked becoming "box-ticking". | Same | Page read |
| Ombudsman: "Rigid or automated systems might unintentionally filter out complex cases or miss signs of vulnerability." Firms use AI to triage, route and analyse sentiment. | https://www.financial-ombudsman.org.uk/data-insight/our-insight/embracing-ais-transformational-impact-consumer-complaints | Page read |
| Ombudsman: in a small sample, up to a third of consumer-side submissions to initial assessment looked AI-assisted. This is complainants, not firms. | Same | Page read |
| FCA April 2024 AI Update: no AI-specific rules; rely on Consumer Duty and SM&CR. | twobirds.com summary | Snippet only |

No published bank case study with figures for AI in complaints was found. Vendor AI claims above carry no outcome figures.

## Not verified

- Channel mix and who logs each channel.
- Cases-per-day targets, quality-check sampling rates, QA checker role.
- Repeat-contact findings.
- Deadline-timer features in Respond, Salesforce, NICE, ServiceNow, Workpro.
- Pega complaint drafting. Only dispute summaries seen.
- FSA 2010 banking review text; TR14/18 PDF text (PDFs unreadable).
- Whether the FCA complaints review quote on logging dates from 2024.
