# Loop log

The prototype was built task by task. A builder agent wrote each task with tests, a separate read-only reviewer agent read the result, and a controller kept a ledger. Defects went back to a builder as a fix round. This page is taken from that ledger (`progress.md`). Where the ledger has no figure, this page says so and does not guess. The loop is drawn in [build-loop.svg](diagrams/build-loop.svg).

## Per task

"Defects" counts the reviewer's numbered findings plus findings from the automated security check, as the ledger records them. A dash means the ledger does not say.

| Task | Builder model | Reviewer model | Fix rounds | Defects found, and the most telling one | Tokens |
|---|---|---|---|---|---|
| 1 Schema, audit log, config | not recorded | not recorded | 1 (plus a NOT NULL repair) | 7 findings, plus 1 medium security finding. `verify_chain` could not see the newest audit rows being deleted | not recorded |
| 2 Masking, deadlines, citation check | not recorded | not recorded | 3 | 3 Important, then 9 more items, then 3 found by the controller. A card number written after a date was left unmasked | not recorded |
| 3 Synthetic data generator | not recorded | not recorded | 2 | Several, count not recorded. Field labels in the notes leaked the answer to the classifier | not recorded |
| 4 Classifiers, search | not recorded | Sonnet | 2 | 3 Important, 11 items in all. Train and test text could overlap. Honest figure fell from 0.894 to 0.844 | review 87k |
| 5 Recorded drafts | not recorded | Sonnet | 2 | 4 Important, 15 items in all. A note containing `</notes>` closed the data block | not recorded |
| 6 Case actions | not recorded | Sonnet | 1 | 10 items. The audit log stored full unmasked claim text, and any specialist could unmask any case | not recorded |
| 7 App shell | not recorded | not recorded | 2 | 6 Important, then 2 more. The Host check ran only on POST requests | not recorded |
| 8 Case view | not recorded | Sonnet | 2 | 15 items, then 8 minors. A GET request wrote claims to the database | not recorded |
| 9 Overview, Departments | not recorded | not recorded | 1 | No Critical. The test suite hung: one test left a transaction open on the shared database | not recorded |
| 10 Pipeline, Team | not recorded | not recorded | 1 | 11 items. The "returned before" urgency reason flagged urgent on 43% of open cases | not recorded |
| 11 Remaining views | not recorded | Sonnet | 0 (minors went to Task 12) | 0 Critical, 0 Important, 13 Minor | builder 183k |
| 12 Polish, bench, README | Opus | folded into the final review | 2 (resumed after turn limits) | The 160,000-case run never finished; the bench reports 16,000 as the largest size measured | builder 170k |
| 13 Deck, diagrams, vault, one-window redesign | controller, four parallel builders (Opus, Sonnet), Codex | Sonnet reviewer for the vault check | see below | The owner rejected the stripped-down screens; see "The redesign" | see below |

## The redesign (11 November)

The owner looked at the running app and said the screens were "horrible" and "too simple": an agent had read "the text is too busy" as "too many charts" and removed them. The owner then asked for every page to fit one window, for tables to stop running down the page, and for a cynical recruiter's eye on clutter. What happened next:

- **The controller built the pattern itself.** Two delegated attempts at the look had been rejected, so the controller wrote the top bar, the stretching charts (`workbench/fluid.py`) and the Overview in a tight edit, screenshot, fix loop, then wrote one spec for the other pages (`fix-one-window.md`).
- **Four builders worked in parallel** on Queue, Case, the work pages and the reference pages. To keep them apart, each page area got its own route module and its own stylesheet, and `app.py` got marked sections before they started.
- **A researcher checked the data sources at source.** Only figures it could open are on the Settings page. DISP rule text could not be opened, so no DISP quote appears.
- **A read-only reviewer checked the screens against the research vault.** Its gaps became features: urgent reasons in lists, missing handover fields before accepting, the clock type, and the AI summary checks panel.
- **Codex drew the case flow diagram** but its sandbox could not write to git. The controller reviewed its three files, ran its nine tests, and committed them with a note saying so.
- **A speed check caught a regression.** The new Overview took 90 ms against a 27 ms before. Reusing counts it already had and one compiled pattern per urgency group brought it to 70 ms.

## What the loop caught

- **A test suite that hung.** The controller found why: one generator test wrote to the shared session database, so a later test blocked at `db.backup`. Fix: that test now uses its own database, plus a guard that fails if the shared one is dirtied.
- **An urgent flag on 43% of cases.** The rule "returned before" made 555 of 1,284 open cases urgent, 195 of them for that reason alone. A flag on that many cases carries no signal, so the reason was removed. Urgent fell to 360.
- **Masking leaks.** Review and a security check found spaced digits, other separators and a card after a date getting through. Three rounds closed them. One miss is still listed: a card with a valid dd-mm-yyyy start keeps up to 8 trailing digits.
- **An evaluation that flattered itself.** Train and test text could overlap, so the first department accuracy (0.894) was too high. After a grouped split it is 0.844.
- **Tamper evidence with a gap.** The audit chain did not notice rows removed from the end. A cheap check was added. Someone who can edit `sqlite_sequence` can still truncate unseen, and the deck says so.

## What it cost

- Tokens: the ledger has figures only for some agents. Task 4 review 87k (Sonnet), Task 11 builder 183k, Task 12 builder 170k, Task 13a builder 76k, stats builder 244k, vault reviewer 145k, source researcher 61k, Codex 59k over three runs. There is no total, so this page gives none.
- Time: not recorded per task.
- Rounds: Task 2 needed the most, three. Some rounds were shared between tasks, so a total would double count and none is given. No task was stopped and sent to the owner.
- Side costs the ledger names: one parallel-writer incident overwrote a Task 2 edit and was redone; six hung test processes had to be killed by hand.

## Rulings

Every `Ruling:` line in the ledger, shortened.

- Generator works at any size; exact counts only at 1,600. The rise is seeded at 1,000 or more.
- The classify command applies the same English check, so a French case shows "needs routing".
- Build on branch `build`, not main.
- Every dispatch also points at `common.md`, because the brief extract leaves out shared decisions.
- Dispatch the next implementer while the previous review runs. Later amended: one writer at a time, because a parallel run lost work.
- Task 1: add a truncation check to the audit chain. An external signed anchor is out of scope.
- Restore NOT NULL on the audit and case columns. A row with no actor is worthless.
- Masking: known values match across whitespace, dot or hyphen. Digit patterns allow separators. Add a catch-all for 8 or more digits. No separator-tolerant catch-all, because it would mask dates and amounts.
- Dates, times and money are held as placeholders before masking. Held only when plausible, so a date-shaped prefix cannot shelter a card.
- Task 3 builder writes the policy clauses itself, not Qwen.
- Classifiers train and predict on note 1 only, the customer's own words.
- Received dates stay skewed to recent weeks, so the volume chart shows 8 weeks.
- Departments with no specialist keep the handler as owner. Team lead owns twice-returned cases.
- Urgent stays 0, not NULL. `handed_over_at` is the latest handover.
- Controller spot check plus the full suite stands in for a third scoped re-review of Tasks 2 and 3.
- Retrieval: section restriction was tried and then reversed on the evidence (12 of 20 against 13 of 20). Case view uses unrestricted search.
- `data/workbench.db` is committed. `data/models/` is rebuilt when missing.
- Held-out split is grouped by normalised note text. This replaced an earlier ruling to leave 0.997 as it was.
- Urgent terms get no negation handling. "No fraud" flags as urgent, which fails safe.
- The footer line "Prototype built for the Ankura AI by Design task. Not an Ankura product." stays.
- No design change from research note 09.
- Overview is cut to a deadline strip, three figures, five cases, one rise line and one chart.
- Cases with no department get no draft.
- The handover suggestion is read from the recording, not a new column.
- A quote that spans a `<` or `>` fails the citation check. It fails safe.
- Any handler may open or approve any case. Ownership changes only through `assign`.
- `reject_draft` removes only claims still in draft status.
- Referrer-Policy `same-origin` replaces `no-referrer`.
- Queue drops the per-row Urgent chip and Details row.
- Deadline strip only on Queue and Overview. Later also removed from Departments, Team and Pipeline.
- Recordings load into claims at startup, not on GET.
- Top words for the predicted department dropped from the case header.
- Demo case is AB-2026-00768.
- After Return, a case is not lifted to the top. Order stays closest deadline first.
- The flow figure (8 clicks, 59 keystrokes) is always published with its caveat.
- No C++ in the pipeline. Measured about 4.5 ms per complaint; the only slow stage is the recorded model draft.
- Overview chart becomes plain columns.
- "Returned before" removed as an urgency reason (see above).
- Pipeline band-flow diagram replaced by four stage boxes with counts.
- Overview chart capped at about 160px.
- Calm rule added with an e2e guard: at most 4 cards and 3 headings above the fold.
- The generator writes an audit entry per generated move, so the shipped audit log is not empty.
- Audit role notice stays a plain notice paragraph.
- Task 13a runs in parallel with Task 12, because it owns only `docs/diagrams/`, this file and `vault/`.
