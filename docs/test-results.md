# Test results

## Known misses in masking

Bare first names that are not in the known values are not caught, so "Ann phoned" survives if Ann Smith is not listed for that case. Numbers written with separators other than space, dot, hyphen, slash or underscore, or in unusual groupings, can survive, and non-UK phone formats are not caught unless they are a run of nine or more digits. Separated digit runs of 9 to 12 digits that are not a phone number, sort code or account number can survive.

Dates, times and pound amounts are deliberately left unmasked, so a card or account number written in a date shape, such as 12-34-5678, or a card that has a date or time inside its digit run, is not masked. A sort code written with a slash, or one that looks like a dd/mm/yy date, is not masked. A date of birth is masked only when it is in the known values for the case.
