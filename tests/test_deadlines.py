from datetime import date, datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from workbench.deadlines import add_business_days, business_days_left, deadline_for


@pytest.fixture
def hol(cfg):
    return {date.fromisoformat(d) for d in cfg["bank_holidays"]}


def test_eight_weeks(cfg):
    assert deadline_for(date(2026, 9, 15), "other", cfg) == date(2026, 11, 10)


def test_payment_skips_weekend_and_holiday(cfg):
    # Received Fri 18 Dec 2026 (day 0). Holidays: Fri 25 Dec, Mon 28 Dec, Fri 1 Jan.
    # Mon 21=1, Tue 22=2, Wed 23=3, Thu 24=4; 25 holiday, 26-27 weekend, 28 holiday;
    # Tue 29=5, Wed 30=6, Thu 31=7; 1 Jan holiday, 2-3 weekend;
    # Mon 4=8, Tue 5=9, Wed 6=10, Thu 7=11, Fri 8=12; 9-10 weekend;
    # Mon 11=13, Tue 12=14, Wed 13 Jan 2027=15.
    assert deadline_for(date(2026, 12, 18), "payment", cfg) == date(2027, 1, 13)


def test_business_days_left(hol):
    assert business_days_left(date(2026, 11, 13), date(2026, 11, 10), hol) == 3
    assert business_days_left(date(2026, 11, 10), date(2026, 11, 10), hol) == 0
    assert business_days_left(date(2026, 11, 9), date(2026, 11, 10), hol) == -1


def test_business_days_left_rejects_datetime(hol):
    with pytest.raises(TypeError):
        business_days_left(date(2026, 11, 13), datetime(2026, 11, 10, 9, 0), hol)


_dates = st.dates(date(2026, 1, 1), date(2027, 6, 30))


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(_dates)
def test_deadline_within_rule(cfg, received):
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    assert deadline_for(received, "other", cfg) == received + timedelta(days=56)
    d = deadline_for(received, "payment", cfg)
    assert received < d <= received + timedelta(days=35)
    assert d.weekday() < 5 and d not in hol
    assert business_days_left(d, received, hol) == 15
    assert add_business_days(received, 15, hol) == d


@settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(_dates, _dates)
def test_days_left_is_int_for_dates(cfg, a, b):
    hol = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    r = business_days_left(a, b, hol)
    assert type(r) is int
    assert (r < 0) if a < b else (r >= 0)


def test_weekend_only_gap_is_negative(hol):
    assert business_days_left(date(2026, 11, 14), date(2026, 11, 15), hol) < 0


def test_unknown_product_kind_rejected(cfg):
    with pytest.raises(ValueError):
        deadline_for(date(2026, 11, 10), "mortgage", cfg)
