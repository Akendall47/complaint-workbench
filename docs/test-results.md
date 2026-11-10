# Test results

## Known misses in masking

Bare first names that are not in the known values are not caught, so "Ann phoned" survives if Ann Smith is not listed for that case. Numbers written with separators other than space, dot, hyphen, slash or underscore, or in unusual groupings, can survive, and non-UK phone formats are not caught unless they are a run of nine or more digits. A card number whose first three groups form a valid dd-mm-yyyy date keeps up to 8 trailing digits. Separated digit runs of 9 to 12 digits that are not a phone number, sort code or account number can survive.

Dates, times and pound amounts are deliberately left unmasked, so a card or account number written in a date shape, such as 12-34-5678, or a card that has a date or time inside its digit run, is not masked. A sort code written with a slash, or one that looks like a dd/mm/yy date, is not masked. A date of birth is masked only when it is in the known values for the case.

## Policy search

Plain BM25 over the whole of note 1 puts the right clause in the top five for 13 of 20 labelled cases (10 of 20 for the key sentence alone). Tried and rejected: limiting the search to the case's department section plus "Complaint handling" gave 11 of 20 for the whole note and 13 of 20 for the key sentence, so the case path uses the unrestricted search. The `sections` argument stays as an optional filter. Queries use their first 50 tokens only.

## Known limits

Urgent terms ignore negation: "I am not struggling to pay" still counts as hardship. Over-flagging is the safe side for a triage tool.

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

## Drafts

Model `qwen3:4b-instruct`, prompt version 2, seed 7, run locally through Ollama. One run over the chosen cases; no case was re-run or hand-picked.

- Cases recorded: 150
- Invalid outputs (not JSON, wrong shape or an error): 0
- Claims: 864
- Claims failing the citation check: 42 (4.9%)
- Seconds per draft: median 12.0, 95th percentile 13.2
- Total model time: 29.9 minutes
