import re
from datetime import date
from typing import Mapping

from workbench.deadlines import business_days_left

_GROUPS = [("Signs of a vulnerable customer", "vulnerability_terms"), ("Financial hardship", "hardship_terms"),
           ("Ongoing fraud", "fraud_terms")]


def _norm(s: str) -> str:
    return s.casefold().replace("’", "'")


def _mentions(text: str, terms: list[str]) -> bool:
    # Whole words or phrases; a short suffix is allowed because the config lists a stem ("impersonat").
    return any(re.search(r"(?<!\w)" + re.escape(_norm(t)) + r"m?(?:e?s|e?d|ing|ions?|ors?|ers?)?(?!\w)", text) for t in terms)


def urgent_reasons(case: Mapping, notes_text: str, today: date, cfg: dict) -> list[str]:
    u, out = cfg["urgent"], []
    if case["state"] != "accepted" and case["deadline"]:
        holidays = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
        left = business_days_left(date.fromisoformat(case["deadline"]), today, holidays)
        if left < 0:
            out.append("Past deadline")
        elif left <= u["deadline_within_business_days"]:
            out.append("Deadline within 5 business days")
    text = _norm(notes_text)
    out += [label for label, key in _GROUPS if _mentions(text, u[key])]
    if (case["return_count"] or 0) >= 1:
        out.append("Returned before")
    return out


def is_urgent(case: Mapping, notes_text: str, today: date, cfg: dict) -> bool:
    if case["urgent_manual"] is not None:
        return bool(case["urgent_manual"])
    return bool(urgent_reasons(case, notes_text, today, cfg))
