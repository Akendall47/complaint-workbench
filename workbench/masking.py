import re

KNOWN_TOKENS = {"name": "[NAME]", "address": "[ADDRESS]", "dob": "[DOB]"}
TOKENS = {"sort_code_account": "[SORT CODE] [ACCOUNT]"}
# Email first, then card, sort code plus account, sort code, account, phone;
# the 9+ digit catch-all runs last. Unlisted patterns go in between.
FIRST = ["email", "card", "sort_code_account", "sort_code", "account", "phone"]
LAST = ["number"]
# Case references and clause numbers must reach the quote check unchanged. Only the exact
# shape is protected, and only when no digit follows; a following separator plus digits is
# left to the normal patterns.
PROTECTED = re.compile(r"\bAB-\d{4}-\d{5}(?!\d)|\bPOL-\d{1,2}(?:\.\d{1,2}){0,3}(?!\d)")
HOLD = ""  # private-use stand-in for held text; no pattern matches it
HOLD2 = ""
PUA = re.compile("[-]")
# Dates, times and money pass through unchanged. A hyphen, dot or space date with a
# 2-digit year is not held: it has the sort code shape.
DATES = re.compile(
    r"(?<!\d)(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2}|\d{1,2}:\d{2})(?!\d)"
    r"|£(?:\d{1,3}(?:,\d{3})+|\d{1,7})(?:\.\d{2})?(?!\d)"
)


def mask(text: str, known: dict[str, str], patterns: dict[str, str]) -> str:
    refs: list[str] = []
    dates: list[str] = []

    def hold_ref(m):
        refs.append(m.group())
        return HOLD

    def hold_date(m):
        dates.append(m.group())
        return HOLD2

    text = PUA.sub("", text)
    text = PROTECTED.sub(hold_ref, text)
    values = sorted(((v.strip(), t) for k, t in KNOWN_TOKENS.items() if (v := known.get(k)) and v.strip()),
                    key=lambda x: -len(x[0]))
    if values:
        # One pass, so a replacement token is never searched again.
        alts = [r"(?<!\w)" + r"\s+".join(map(re.escape, v.split())) + r"(?!\w)" if len(v) < 3
                else r"\s+".join(map(re.escape, v.split())) for v, _ in values]
        rx = re.compile("|".join(f"(?P<g{i}>{a})" for i, a in enumerate(alts)), re.I)
        text = rx.sub(lambda m: values[int(m.lastgroup[1:])][1], text)
    text = DATES.sub(hold_date, text)
    names = FIRST + [n for n in patterns if n not in FIRST + LAST] + LAST
    for name in (n for n in names if n in patterns):
        token = TOKENS.get(name, f"[{name.upper().replace('_', ' ')}]")
        text = re.sub(patterns[name], token, text, flags=re.I)
    # Each kind keeps its own order, so one pass per kind restores it.
    r, d = iter(refs), iter(dates)
    return re.sub(f"{HOLD}|{HOLD2}", lambda m: next(r if m.group() == HOLD else d), text)
