from datetime import date

import pytest

from workbench.urgency import is_urgent, urgent_reasons

TODAY = date(2026, 11, 10)


def case(**kw):
    base = {"state": "in_review", "deadline": "2026-12-30", "return_count": 0, "urgent_manual": None}
    return {**base, **kw}


@pytest.mark.parametrize("c, text, reason", [
    (case(deadline="2026-11-13"), "all fine", "Deadline within 5 business days"),
    (case(deadline="2026-11-01"), "all fine", "Deadline within 5 business days"),
    (case(), "My husband has Dementia.", "Signs of a vulnerable customer"),
    (case(), "I am behind on payments and cannot afford rent.", "Financial hardship"),
    (case(), "It was a SCAM by a fraudster.", "Ongoing fraud"),
    (case(return_count=1), "all fine", "Returned before"),
])
def test_each_reason_fires_alone(cfg, c, text, reason):
    assert urgent_reasons(c, text, TODAY, cfg) == [reason]


def test_quiet_case_not_urgent(cfg):
    assert urgent_reasons(case(), "I was charged a fee.", TODAY, cfg) == []


def test_accepted_ignores_deadline(cfg):
    assert urgent_reasons(case(state="accepted", deadline="2026-11-01"), "", TODAY, cfg) == []


def test_whole_words_only(cfg):
    assert urgent_reasons(case(), "a scholar ate scampi, with scarcely a carerless word", TODAY, cfg) == []
    assert urgent_reasons(case(), "Someone impersonated my bank", TODAY, cfg) == ["Ongoing fraud"]
    assert urgent_reasons(case(), "Can’t afford it", TODAY, cfg) == ["Financial hardship"]


def test_order(cfg):
    r = urgent_reasons(case(deadline="2026-11-11", return_count=2), "cancer, food bank, phishing", TODAY, cfg)
    assert r == ["Deadline within 5 business days", "Signs of a vulnerable customer", "Financial hardship",
                 "Ongoing fraud", "Returned before"]


def test_manual_override(cfg):
    assert is_urgent(case(urgent_manual=0, return_count=3), "", TODAY, cfg) is False
    assert is_urgent(case(urgent_manual=1), "", TODAY, cfg) is True
    assert is_urgent(case(return_count=1), "", TODAY, cfg) is True


def test_scammed_counts_as_fraud(cfg):
    assert urgent_reasons(case(), "I was scammed yesterday and payments are still leaving", TODAY, cfg) == ["Ongoing fraud"]
