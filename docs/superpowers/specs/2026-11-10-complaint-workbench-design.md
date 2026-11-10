# Complaint Workbench: design

Date: 2026-11-10. Deadline for submission: Wednesday 11 November 2026, 5:30pm GMT.

Items marked **(owner)** were decided by the project owner. Items marked **(my call)** were chosen by the design author and can be overruled.

## 1. Intent

This is the build task for Ankura's AI by Design internship, banking scenario. A fictional bank has a growing complaints backlog. Staff lose time finding information across case notes and policy documents, and specialist teams receive incomplete handovers.

The submission is a working prototype plus supporting material. The owner wants the reviewer to remember it as elegant, not over-engineered, novel, well tested, well documented and easy to understand. **(owner)**

The central argument of the submission: use the cheapest tool that does each job well, and build the controls into the interface. Plain code and a small classifier do the sorting and searching. A language model only drafts, and every sentence it drafts must point to a source. A person approves everything. Ankura describes governance as "an engineering and UX problem, not only policy", and this prototype is built to show that.

## 2. Goals

1. A complaints handler can open a case, read masked notes, check an AI-drafted summary against its sources, see the policy clauses that apply, complete a handover pack, and approve or reject it.
2. A specialist team can see the handovers sent to it and return an incomplete one with a reason.
3. A team lead can see the state of the backlog on an opening dashboard and drill into departments and sources.
4. A reviewer can run it with one command, with no API key, no account and no cost. **(owner)**
5. The controls are visible features: masking, source-linked claims, per-claim confirmation, a reason on rejection, an audit trail.
6. The build itself demonstrates a multi-agent closed loop using Claude, Codex and a local open model, with token use measured. **(owner)**

## 3. Non-goals

- Real authentication. A role switcher stands in for login, and this is stated as a limitation.
- Real or scraped data. The brief requires fictional or synthetic data only.
- Drafting replies to customers, or recommending an outcome or redress amount.
- Root-cause clustering. Considered and left out to protect the deadline. **(my call)**
- Vector search. Added only if measured retrieval quality requires it.

## 4. Anti-goals

The submission fails, even if it runs, if any of these is true:

- The AI appears to decide a complaint, or a case can be approved without a person checking the claims.
- An AI claim with no matching source passage is shown as if it were supported.
- The reviewer needs a key, an account or a paid service to try it.
- The interface looks like a generated template. The first mockup was rejected by the owner as poor design.
- Any figure or rule in the deck or report is unverified but presented as fact.

## 5. Users and views

Left-side navigation, one job per view. **(owner: dashboard landing page, left navigation, department and source views, not one screen doing everything)**

| View | For | Job |
|---|---|---|
| Overview (landing) | Team lead | Morning check: headline figures and charts |
| Departments | Specialist teams, team lead | One team's workload, its incoming handovers, and the fields most often missing. Also filters by source channel |
| Queue | Handler | Pick the next case, sorted by days left |
| Case | Handler | Do the work: notes, claims, sources, policy, handover, approve or reject |
| Policy library | Everyone | Search and read the bank's policy clauses |
| Audit log | Team lead, reviewer | Every action, who took it and when |
| Settings | Team lead | Read-only view of the few settings that matter |

Overview charts **(owner: "nice charts")**: 8-week trend of new versus closed complaints, open complaints by department, complaints by source, and cases by days left to deadline. Headline figures: open, due within 5 business days, past deadline, average days open, share of handovers returned as incomplete. Clicking a chart segment opens the matching filtered view.

Departments: Fraud claims, Financial difficulty, Bereavement, Data protection, Mis-selling review, General service. Sources: phone, mobile app, secure message, branch, letter, email.

Roles **(my call)**: handler, specialist, team lead, chosen from a switcher in the header. The role is recorded in the audit log with each action.

Visual design **(owner)**: minimal and elegant in the manner of Apple's own apps, and still effective for dense case work. Where the two conflict, effective wins. Claude and Codex design it together: one drafts, the other critiques and revises. A Codex redesign of the mockup is in progress. The look is not approved yet. The builder implements the structure above and applies the approved mockup's styling once the owner signs it off. Fixed rules regardless of styling: system fonts, no external requests, status never shown by colour alone, WCAG 2.2 AA, fully keyboard operable, charts as server-rendered inline SVG with values labelled directly.

## 6. The case flow

1. The handler opens a case from the queue. The notes are shown with customer details masked.
2. The summary appears as separate claims, labelled as an AI draft. Each claim carries a numbered citation. Selecting it highlights the source passage in the notes.
3. A claim whose quoted source is not found word for word in the notes is marked "unsupported" and cannot be confirmed. The handler can remove or rewrite it.
4. Claims the model inferred rather than read, such as possible vulnerability, carry a "check this" flag instead of a confidence percentage.
5. The policy clauses that match the case are listed with clause numbers, each opening in the policy library.
6. The handover pack lists the fields the receiving department needs. Missing fields are named, with the action needed to fill them.
7. Approve stays locked until every claim is confirmed, edited or removed. Reject requires a written reason. A pack sent with fields still missing is marked incomplete.
8. The specialist sees the handover in the Departments view and can accept it, or return it with a reason. Returned handovers feed the dashboard figure.
9. Every step writes an audit entry.

## 7. Where each technique is used

| Job | Technique | Why |
|---|---|---|
| Route a complaint to a department | TF-IDF plus logistic regression (scikit-learn) | Runs in milliseconds on a CPU, costs nothing per case, and can show which words drove the result. **(owner: hand-built ML where a language model is not needed)** |
| Find policy clauses and past notes | SQLite FTS5 with BM25 ranking | Exact on clause numbers, one auditable file, no extra service |
| Mask customer details | Known-field replacement plus patterns for account numbers, sort codes, phone numbers, emails and postcodes | Deterministic and testable. Runs before any text reaches a model |
| Check citations | Word-for-word match of each quoted source against the notes | A hard check, not a model's opinion |
| Work out deadlines and missing fields | Plain rules read from configuration | Regulatory clocks must not be probabilistic |
| Draft the claim-by-claim summary and suggest handover field values | Language model with output forced to a JSON schema | The one job that needs language understanding |

Routing below a confidence threshold goes to a person and is shown as "needs routing". The threshold is a setting.

## 8. AI answers are recorded

**(owner)** The reviewer must not need a key or pay anything, so the language-model output for every synthetic case is recorded in advance and shipped in the repo.

- The recordings come from an open-weight model running locally through Ollama, to show that customer data never needs to leave the bank's own hardware. **(owner: open model, on-prem)**
- Model **(my call)**: an Apache-2.0 Qwen model. `qwen3:4b-instruct` is already installed. If its drafts are too weak, the builder pulls a larger Qwen that fits 8 GB of VRAM.
- Each recording stores the model name, the prompt version, the masked input and the raw output, so a reviewer can see exactly what the model was given.
- The recording script is in the repo, so the recordings can be regenerated. A live mode calls Ollama when it is running. Recorded mode is the default.
- The recorded output passes through the same schema validation and citation check at display time as live output would. The controls are exercised for real, not bypassed.

## 9. Data

- All data is synthetic. No Kaggle or regulator complaint text is used, because the public complaint datasets contain real people's complaints. **(my call, following the brief)**
- A seeded generator script produces the cases: notes, department, source, dates, customer fields and the true values of the handover fields. At least 120 cases. Category and channel proportions are loosely shaped on published FCA totals and described as illustrative.
- The policy library is a set of about 40 fictional clauses written for this bank, with clause numbers.
- A handful of cases are adversarial on purpose: complaint text containing hidden instructions, and notes with details that should be masked in unusual formats.
- The classifier is trained and tested on synthetic text. The report states that its accuracy will be higher than on real complaints.

## 10. Controls and security

| Risk | Control in the prototype |
|---|---|
| Instructions hidden in complaint text | Notes are passed to the model as delimited data. The model has no tools and no network access. Output must match a schema. Links and images are stripped from output. Adversarial cases are in the test set |
| Invented facts or policy | Word-for-word citation check. Policy clauses come from search, never from the model |
| Customer data exposure | Masking before the model and on screen. Unmasking is a logged action with a reason |
| Rubber-stamping | Per-claim confirmation, a reason on rejection, no confidence percentages, and edits and overrides logged |
| Tampering with the record | The audit log is append-only and each entry stores a hash of the previous one, so a changed entry is detectable. **(my call)** |
| Third-party dependence | Local open model, a single SQLite file, no external requests from the browser |
| Web basics | Output escaping in templates, parameterised queries, input validation on every form |

Stated limitations: no real authentication or access control, masking patterns tuned to synthetic data, and a hash chain that detects tampering but does not prevent it.

## 11. Performance

**(owner: low latency and well-optimised database retrieval)**

- Target: server response under 100 ms at the 95th percentile for every view on the synthetic data set, measured by a benchmark script whose results go in the report.
- Indexed columns for every filter the queue and dashboard use. Dashboard figures come from single aggregate queries.
- Server-rendered HTML with small fragment updates. No build step and no front-end framework.

## 12. Configuration

**(owner: easy to change in the backend, only what is needed shown in the frontend)**

One configuration file holds departments, required handover fields per department, deadline rules, the routing threshold, masking patterns and the model name. Adding a department or a required field is a change to that file, with no code change. The Settings view shows a short read-only subset. **(my call: read-only)**

## 13. Technology

**(my call)** Python 3.11, FastAPI, Jinja2 templates, htmx, SQLite with FTS5, scikit-learn, `uv` for the environment. Tests with pytest and Playwright. One command starts it. A hosted copy on a free tier is a stretch goal, not a requirement.

## 14. Testing

- Unit tests: masking, citation check, deadline calculation in business days, missing-field rules, audit hash chain.
- Classifier: accuracy and per-department results on held-out cases, with a confusion matrix in the report.
- Retrieval: a small labelled set of case-to-clause matches, reporting how often the right clause is in the top five.
- Latency benchmark against the 100 ms target.
- Adversarial cases: hidden instructions and unusual detail formats.
- Browser tests with Playwright: Approve is locked until claims are confirmed, Reject needs a reason, the full flow from queue to specialist return, keyboard-only operation.
- The report states what was not tested.

## 15. How it is built: the multi-agent closed loop

**(owner)** The build uses a closed loop and records it, so the method can be discussed at interview.

- Claude leads: it plans, splits the work into small tasks with a pass condition each, and decides when a task is done.
- Claude and Codex both build, each in files they own.
- The local Qwen model does cheap bounded jobs, such as generating synthetic cases.
- Each model reviews the other's work.
- Per task: write the task, build with tests, run the tests, cross-review, feed failures back, repeat. The loop closes when tests pass and the review is clean. After three failed rounds it stops and goes to the owner.
- Recorded per round: tokens per agent and model, defects found and which model caught them, rounds needed, time taken. Token counts come from the tools' local logs.

The design step already followed this pattern: Claude drafted a mockup, the owner rejected it, and Codex redesigned it.

## 16. Deliverables

1. The working prototype in a GitHub repository, with a README giving run and test instructions.
2. A five-slide deck, the official supporting document within the brief's five-page limit. One slide each for: the problem and approach, the build and AI tools, tests with results and limits, controls and human review, effects on staff. **(owner)**
3. A LaTeX technical sheet, labelled as an optional appendix: architecture, data model, controls, test results, token measurements. **(owner)**
4. The Obsidian vault in `vault/`: research with sources, decisions, the loop log. **(owner)**
5. Diagrams: system architecture, the case flow, the staff handoff before and after, and the build loop. **(owner)**
6. A knowledge graph of the repository made with graphify. **(owner)**

The deck must cover the brief's five considerations: business value, risks and controls and human oversight, changes to roles and workflows, assumptions and limitations and trade-offs, and the AI tools used with an honest assessment of each.

## 17. Order of work if time runs short

The deadline is about one day away. If something must be cut, cut from the bottom.

1. Case flow with recorded AI, masking, citation check, audit log, tests.
2. Queue, Overview dashboard, README, deck.
3. Departments view with specialist return, routing classifier.
4. Policy library, Audit log and Settings views.
5. LaTeX sheet, diagrams, loop log with token figures.
6. Knowledge graph, hosted copy.

## 18. Before anything is quoted

The research notes in `vault/research/` mark several items as unverified, including the FCA complaint time limits and several regulatory references. Each is checked against a primary source before it appears in the product, deck or report. Anything that cannot be verified is stated as an assumption or left out. No cost-per-complaint figure was found, so the value case uses a stated assumption.

## 19. Left to the builder

File layout, database schema, exact prompts, the number of synthetic cases above the minimum, chart drawing code, and the wording of fictional policy clauses.

## 20. Known gaps in tooling

No LaTeX engine and no `ccusage` are installed on the build machine. Both need installing before items 3 and 4 of the deliverables can be completed.
