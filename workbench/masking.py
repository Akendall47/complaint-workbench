import re

KNOWN_TOKENS = {"name": "[NAME]", "address": "[ADDRESS]", "dob": "[DOB]"}
TOKENS = {"sort_code_account": "[SORT CODE] [ACCOUNT]"}
# Email first (bounded), then card, sort code plus account, sort code, account, phone;
# the 9+ digit catch-all runs last. Unlisted patterns go in between.
FIRST = ["email", "card", "sort_code_account", "sort_code", "account", "phone"]
LAST = ["number"]
# Case references and clause numbers must reach the quote check unchanged.
PROTECTED = re.compile(r"\bAB-\d{4}-\d{5}\b|\bPOL-\d+(?:\.\d+)*\b")
HOLD = 0xE000  # private-use characters stand in for protected text; no pattern matches them


def mask(text: str, known: dict[str, str], patterns: dict[str, str]) -> str:
    held: list[str] = []

    def hold(m):
        held.append(m.group())
        return chr(HOLD + len(held) - 1)

    text = PROTECTED.sub(hold, text)
    values = sorted(((v.strip(), KNOWN_TOKENS[k]) for k, v in known.items() if v and len(v.strip()) >= 3),
                    key=lambda x: -len(x[0]))
    for value, token in values:
        pat = r"\s+".join(map(re.escape, value.split()))
        text = re.sub(pat, token, text, flags=re.I)
    names = FIRST + [n for n in patterns if n not in FIRST + LAST] + LAST
    for name in (n for n in names if n in patterns):
        token = TOKENS.get(name, f"[{name.upper().replace('_', ' ')}]")
        text = re.sub(patterns[name], token, text, flags=re.I)
    for i, original in enumerate(held):
        text = text.replace(chr(HOLD + i), original)
    return text
