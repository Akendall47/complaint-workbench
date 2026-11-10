# Test results

## Known misses in masking

Bare first names that are not in the known values are not caught, so "Ann phoned" survives if Ann Smith is not listed for that case. Numbers written with separators other than space, dot or hyphen, such as slashes or underscores, or in unusual groupings, can survive. Phone numbers in non-UK formats are not caught unless they happen to be a run of nine or more digits.
