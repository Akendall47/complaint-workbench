# Test results

## Known misses in masking

Bare first names that are not in the known values are not caught, so "Ann phoned" survives if Ann Smith is not listed for that case. Numbers written with separators other than space, dot, hyphen, slash or underscore, or in unusual groupings, can survive, and non-UK phone formats are not caught unless they are a run of nine or more digits. A card number whose first three groups form a valid dd-mm-yyyy date keeps up to 8 trailing digits. Separated digit runs of 9 to 12 digits that are not a phone number, sort code or account number can survive.

Dates, times and pound amounts are deliberately left unmasked, so a card or account number written in a date shape, such as 12-34-5678, or a card that has a date or time inside its digit run, is not masked. A sort code written with a slash, or one that looks like a dd/mm/yy date, is not masked. A date of birth is masked only when it is in the known values for the case.

## Classifiers

Both models read note 1 only, the customer's own words, because routing happens before staff notes exist. Labels are the generator's `department_true` and `type_true`. Split: 80/20, seed 7. Figures come from `uv run python -m workbench.classify`; the generated labels carry deliberate noise, so these are not real-world figures.

### Department routing

Accuracy on the held-out 20% (320 cases): **0.894**.

Cases below the routing threshold (0.45): 11.3%. Accuracy counting only predictions at or above it: 0.926.

| Class | Test cases | Precision | Recall |
|---|---|---|---|
| Bereavement | 34 | 1.00 | 0.94 |
| Data protection | 14 | 0.86 | 0.43 |
| Financial difficulty | 63 | 0.95 | 0.87 |
| Fraud claims | 57 | 0.90 | 0.93 |
| General service | 124 | 0.83 | 0.96 |
| Mis-selling review | 28 | 1.00 | 0.75 |

Confusion table (rows are the true class, columns the predicted class):

| True \ predicted | Bereavement | Data protection | Financial difficulty | Fraud claims | General service | Mis-selling review |
|---|---|---|---|---|---|---|
| Bereavement | 32 | 0 | 0 | 0 | 2 | 0 |
| Data protection | 0 | 6 | 0 | 2 | 6 | 0 |
| Financial difficulty | 0 | 0 | 55 | 2 | 6 | 0 |
| Fraud claims | 0 | 0 | 0 | 53 | 4 | 0 |
| General service | 0 | 1 | 2 | 2 | 119 | 0 |
| Mis-selling review | 0 | 0 | 1 | 0 | 6 | 21 |

Most confused pairs: Mis-selling review read as General service (6); Data protection read as General service (6); Financial difficulty read as General service (6).

### Complaint type

Accuracy on the held-out 20% (320 cases): **0.997**.

Cases below the routing threshold (0.45): 1.2%. Accuracy counting only predictions at or above it: 1.000.

| Class | Test cases | Precision | Recall |
|---|---|---|---|
| Account administration | 74 | 1.00 | 1.00 |
| Fees and charges | 54 | 1.00 | 1.00 |
| Fraud or security | 31 | 1.00 | 1.00 |
| Investment advice | 20 | 1.00 | 1.00 |
| Other | 1 | 0.00 | 0.00 |
| Payment scam | 30 | 1.00 | 1.00 |
| Service | 61 | 0.98 | 1.00 |
| Website or app | 49 | 1.00 | 1.00 |

Confusion table (rows are the true class, columns the predicted class):

| True \ predicted | Account administration | Fees and charges | Fraud or security | Investment advice | Other | Payment scam | Service | Website or app |
|---|---|---|---|---|---|---|---|---|
| Account administration | 74 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fees and charges | 0 | 54 | 0 | 0 | 0 | 0 | 0 | 0 |
| Fraud or security | 0 | 0 | 31 | 0 | 0 | 0 | 0 | 0 |
| Investment advice | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 |
| Other | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| Payment scam | 0 | 0 | 0 | 0 | 0 | 30 | 0 | 0 |
| Service | 0 | 0 | 0 | 0 | 0 | 0 | 61 | 0 |
| Website or app | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 49 |

Most confused pairs: Other read as Service (1).
