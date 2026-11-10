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
HOLD = 0xE000  # private-use characters stand in for protected text; no pattern matches them
PUA = re.compile("[-]")


def mask(text: str, known: dict[str, str], patterns: dict[str, str]) -> str:
    held: list[str] = []

    def hold(m):
        held.append(m.group())
        return chr(HOLD + len(held) - 1)

    text = PUA.sub("", text)
    text = PROTECTED.sub(hold, text)
    values = sorted(((v.strip(), t) for k, t in KNOWN_TOKENS.items() if (v := known.get(k)) and v.strip()),
                    key=lambda x: -len(x[0]))
    if values:
        # One pass, so a replacement token is never searched again.
        alts = [r"(?<!\w)" + r"\s+".join(map(re.escape, v.split())) + r"(?!\w)" if len(v) < 3
                else r"\s+".join(map(re.escape, v.split())) for v, _ in values]
        rx = re.compile("|".join(f"(?P<g{i}>{a})" for i, a in enumerate(alts)), re.I)
        text = rx.sub(lambda m: values[int(m.lastgroup[1:])][1], text)
    names = FIRST + [n for n in patterns if n not in FIRST + LAST] + LAST
    for name in (n for n in names if n in patterns):
        token = TOKENS.get(name, f"[{name.upper().replace('_', ' ')}]")
        text = re.sub(patterns[name], token, text, flags=re.I)
    for i, original in enumerate(held):
        text = text.replace(chr(HOLD + i), original)
    return text
