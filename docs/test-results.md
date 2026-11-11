# Test results

## Summary
Every figure comes from one command: `uv run python tests/bench/bench.py --suites`. Machine: Windows-11-10.0.26300-SP0, AMD64 Family 25 Model 116 Stepping 1, AuthenticAMD, Python 3.13.16. All data is synthetic.

| What | Result | Limit |
|---|---|---|
| Scale | 1,600 cases: Queue 20.6 ms median, 25.4 ms p95; 16,000 cases: Queue 68.8 ms, 78.86 ms p95 | Synthetic data, one machine, no network |
| Slowest page | /audit at 63.79 ms median (budget 100 ms) | Median of 20 requests per view, 1,600 cases |
| Routing | 84.4% overall; 90.5% when sent on; 11.3% go to a person | Held-out 20% of synthetic labels |
| Complaint type | 99.4% | Synthetic labels, so this is flattering |
| Policy search | 13 of 20 right clause in top five | Hand-labelled set of 20 |
| Citation check | 42 of 864 claims fail | Recorded drafts, 150 cases |
| Masking | 21 of 22 test strings caught | A small test set, not real data |
| Injection | 0 of 1 recorded drafts changed | Hidden-instruction cases |
| Audit tamper | detected | Edit of one row, chain check |
| Queue to approved | 8 clicks, 59 keystrokes | Queue opened by filtered URL; filter clicks not counted |
| Tests | 423 (380 unit and property, 43 browser) | Counted by pytest --collect-only |
| Draft speed | 12.0 s median, 13.2 s p95 | Local qwen3:4b-instruct, recorded in advance |
| Slowest stage | 2.57 ms median | Per stage, 500 notes |

## Known misses in masking

Bare first names that are not in the known values are not caught, so "Ann phoned" survives if Ann Smith is not listed for that case. Numbers written with separators other than space, dot, hyphen, slash or underscore, or in unusual groupings, can survive, and non-UK phone formats are not caught unless they are a run of nine or more digits. A card number whose first three groups form a valid dd-mm-yyyy date keeps up to 8 trailing digits. Separated digit runs of 9 to 12 digits that are not a phone number, sort code or account number can survive.

Dates, times and pound amounts are deliberately left unmasked, so a card or account number written in a date shape, such as 12-34-5678, or a card that has a date or time inside its digit run, is not masked. A sort code written with a slash, or one that looks like a dd/mm/yy date, is not masked. A date of birth is masked only when it is in the known values for the case.

## Policy search

Plain BM25 over the whole of note 1 puts the right clause in the top five for 13 of 20 labelled cases (10 of 20 for the key sentence alone). Tried and rejected: limiting the search to the case's department section plus "Complaint handling" gave 11 of 20 for the whole note and 13 of 20 for the key sentence, so the case path uses the unrestricted search. The `sections` argument stays as an optional filter. Queries use their first 50 tokens only.

## Known limits

Urgent terms ignore negation: "I am not struggling to pay" still counts as hardship. Over-flagging is the safe side for a triage tool.

## Drafts

Model `qwen3:4b-instruct`, prompt version 2, seed 7, run locally through Ollama. One run over the chosen cases; no case was re-run or hand-picked.

- Cases recorded: 150
- Invalid outputs (not JSON, wrong shape or an error): 0
- Claims: 864
- Claims failing the citation check: 42 (4.9%)
- Seconds per draft: median 12.0, 95th percentile 13.2
- Total model time: 29.9 minutes

A passing citation check proves only that the quoted words are in the cited note. It does not prove the claim is a fair summary, which is why a person confirms each claim. The 42 failing claims were counted and kept, and are shown to the handler as unsupported. Cases with no department (below the routing threshold) get no draft and show "No draft recorded".

## Volume
Median / 95th centile in ms over 200 requests per view, through `TestClient` (no network). Budget 100 ms. Drafts are not recorded for bench data.

| Cases | Build | Database | / | /queue | /departments | /pipeline | /policies?q=refund | a case page |
|---|---|---|---|---|---|---|---|---|
| 1600 | 0.8 s | 5.0 MB | 27.36 / 33.27 | 20.6 / 25.4 | 16.79 / 21.01 | 32.55 / 37.75 | 14.97 / 19.77 | 21.39 / 30.0 |
| 16000 | 4.7 s | 48.0 MB | 152.98 / 182.55 | 68.8 / 78.86 | 72.98 / 83.5 | 175.67 / 194.04 | 23.97 / 27.68 | 29.25 / 34.5 |

A 160,000 case run was started but did not finish, so the largest size measured is 16,000. Misses at larger sizes are reported, not fixed.

The first size where any view misses 100 ms at the 95th centile is **16,000 cases**.

Slowest of the nine views, median of 20 requests (1,600 cases):

| View | Median / p95 (ms) |
|---|---|
| / | 27.98 / 32.01 |
| /queue | 28.9 / 32.56 |
| /cases/AB-2026-00768 | 25.01 / 38.8 |
| /departments | 22.76 / 26.81 |
| /team | 24.15 / 45.99 |
| /pipeline | 32.86 / 44.23 |
| /policies | 18.19 / 22.35 |
| /audit | 63.79 / 96.0 |
| /settings | 20.04 / 55.07 |

## Speed per stage
500 notes, 1,600-case database. Only the draft (about 12 s) is slow; nothing needed rewriting in a lower-level language.

| Stage | Median (ms) | p95 (ms) |
|---|---|---|
| classify department | 1.54 | 2.21 |
| classify type | 1.49 | 2.19 |
| mask | 0.4 | 0.61 |
| policy search | 2.57 | 3.53 |
| citation check | 0.13 | 0.17 |

## Odd inputs
| Row | Input | Result | Note |
|---|---|---|---|
| 1 | empty or whitespace complaint is rejected | pass |  |
| 2 | very long complaint is stored and handled | pass | Typed text is limited to 5,000 characters; the 50,000 character case is stored from generated data. The draft prompt holds the whole masked note, not retrieved passages. |
| 3 | not english is routed to a person and gets no draft | pass |  |
| 4 | text that instructs the ai is only text | pass |  |
| 5 | personal details in unusual formats are masked | pass |  |
| 6 | no personal details means nothing masked | pass |  |
| 7 | same complaint twice is flagged as duplicate | pass |  |
| 8 | complaint that fits no type shows low confidence | pass | The confidence is low, but the label is not always Other. |
| 9 | two departments about equal needs routing | pass |  |
| 10 | deadline on weekend or bank holiday counts business days | pass |  |
| 11 | case returned twice goes to the team lead | pass |  |
| 12 | citation not in source cannot be confirmed | pass |  |
| 13 | invalid or missing ai answer means no draft | pass |  |
| 14 | two people acting at once second is refused | pass |  |
| 15 | audit rows cannot be changed or deleted | pass |  |

## Security checks
| Kind | Caught | Missed | Missed examples |
|---|---|---|---|
| card | 5 | 0 |  |
| sort code | 3 | 1 | 123456 is my sort code |
| account number | 3 | 0 |  |
| phone | 5 | 0 |  |
| email | 2 | 0 |  |
| postcode | 3 | 0 |  |

Response headers present: content-security-policy, x-content-type-options, referrer-policy. Missing: none. Refused-action checks in the rule tests: 38. Requests to other hosts: every browser page test asserts none (see Browser tests).

## Browser tests
43 browser tests (Playwright, Chromium) on all nine views at 1440, 1100 and 1024 px: no sideways scroll, no console errors, no request to another host, skip link first, every control reachable by keyboard. Last run: 43 passed in 187.08s (0:03:07).

Contrast (WCAG ratio from the CSS colours): lowest 5.48:1, target 4.5:1.

| Pair | Ratio |
|---|---|
| body text (ink on paper) | 14.54 |
| body text (ink on white) | 16.24 |
| muted text on white | 6.72 |
| muted text on paper | 6.02 |
| chip text (ink on #ececf1) | 13.8 |
| warning chip (accent-dark on tint) | 5.48 |
| links (indigo-dark on white) | 8.48 |

Chart label size (14 px at full width) as the page narrows: 639px viewport 13.1 px, 480px viewport 9.6 px, 375px viewport 7.3 px. Computed from the SVG scale, not measured in a browser. Below 640 px the labels fall under 13 px.

Automated accessibility check (axe): not run, it could not be vendored offline.

## Test counts
Unit and property: 380 collected (6 of them property tests). End to end: 43. Total 423.

Last runs: unit and property, 380 passed, 1 warning in 98.26s (0:01:38) (101 s). End to end, 43 passed in 187.08s (0:03:07) (189 s).

## Not tested
Real complaints, real handlers, many users at once beyond two, a live model under load, and a 100,000 case run in a browser. Spec section 26.

## Classifiers

Both models read note 1 only, the customer's own words, because routing happens before staff notes exist. Labels are the generator's `department_true` and `type_true`. Split: 80/20 by group (the normalised note 1 text, so no wording is on both sides), seed 7. Under the earlier plain random split with the same seed, 0 of the 320 test rows shared their normalised text with a training row; every one of the 1,600 note 1 texts is distinct, so the grouped split only changes which 320 cases are held out. Figures come from `uv run python -m workbench.classify`; the generated labels carry deliberate noise, so these are not real-world figures.

### Department routing

Accuracy on the held-out 20% (320 cases): **0.844**.

Cases below the routing threshold (0.45): 11.3%. Accuracy counting only predictions at or above it: 0.905.

| Class | Test cases | Precision | Recall |
|---|---|---|---|
| Bereavement | 29 | 1.00 | 0.93 |
| Data protection | 27 | 0.90 | 0.33 |
| Financial difficulty | 54 | 0.93 | 0.76 |
| Fraud claims | 58 | 0.88 | 0.84 |
| General service | 128 | 0.76 | 0.97 |
| Mis-selling review | 24 | 1.00 | 0.83 |

Confusion table (rows are the true class, columns the predicted class):

| True \ predicted | Bereavement | Data protection | Financial difficulty | Fraud claims | General service | Mis-selling review |
|---|---|---|---|---|---|---|
| Bereavement | 27 | 0 | 0 | 0 | 2 | 0 |
| Data protection | 0 | 9 | 0 | 4 | 14 | 0 |
| Financial difficulty | 0 | 0 | 41 | 2 | 11 | 0 |
| Fraud claims | 0 | 0 | 0 | 49 | 9 | 0 |
| General service | 0 | 1 | 2 | 1 | 124 | 0 |
| Mis-selling review | 0 | 0 | 1 | 0 | 3 | 20 |

Most confused pairs: Data protection read as General service (14); Financial difficulty read as General service (11); Fraud claims read as General service (9).

### Complaint type

Accuracy on the held-out 20% (320 cases): **0.994**.

Cases below the routing threshold (0.45): 2.2%. Accuracy counting only predictions at or above it: 1.000.

| Class | Test cases | Precision | Recall |
|---|---|---|---|
| Account administration | 75 | 0.99 | 1.00 |
| Fees and charges | 46 | 0.98 | 1.00 |
| Fraud or security | 27 | 1.00 | 1.00 |
| Investment advice | 18 | 1.00 | 1.00 |
| Other | 6 | 1.00 | 0.67 |
| Payment scam | 29 | 1.00 | 1.00 |
| Service | 77 | 1.00 | 1.00 |
| Website or app | 42 | 1.00 | 1.00 |

Confusion table (rows are the true class, columns the predicted class):

| True \ predicted | Account administration | Fees and charges | Fraud or security | Investment advice | Other | Payment scam | Service | Website or app |
|---|---|---|---|---|---|---|---|---|
| Account administration | 75 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fees and charges | 0 | 46 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fraud or security | 0 | 0 | 27 | 0 | 0 | 0 | 0 | 0 |
| Investment advice | 0 | 0 | 0 | 18 | 0 | 0 | 0 | 0 |
| Other | 1 | 1 | 0 | 0 | 4 | 0 | 0 | 0 |
| Payment scam | 0 | 0 | 0 | 0 | 0 | 29 | 0 | 0 |
| Service | 0 | 0 | 0 | 0 | 0 | 0 | 77 | 0 |
| Website or app | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 42 |

Most confused pairs: Other read as Fees and charges (1); Other read as Account administration (1).
