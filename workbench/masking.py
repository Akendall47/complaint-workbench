import re

KNOWN_TOKENS = {"name": "[NAME]", "address": "[ADDRESS]", "dob": "[DOB]"}
# Card first: its 13 to 19 digits would otherwise be half-eaten by the account or phone
# pattern. Sort code before account for the same reason. Unlisted patterns run last.
ORDER = ["card", "sort_code", "account", "phone", "email", "postcode"]


def mask(text: str, known: dict[str, str], patterns: dict[str, str]) -> str:
    values = sorted(((v, KNOWN_TOKENS[k]) for k, v in known.items() if v), key=lambda x: -len(x[0]))
    for value, token in values:
        text = re.sub(re.escape(value), token, text, flags=re.I)
    names = [n for n in ORDER if n in patterns] + [n for n in patterns if n not in ORDER]
    for name in names:
        token = f"[{name.upper().replace('_', ' ')}]"
        text = re.sub(patterns[name], token, text, flags=re.I)
    return text
