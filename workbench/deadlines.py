from datetime import date, datetime, timedelta


def _is_business(d: date, holidays: set[date]) -> bool:
    return d.weekday() < 5 and d not in holidays


def add_business_days(start: date, n: int, holidays: set[date]) -> date:
    d = start
    while n > 0:
        d += timedelta(days=1)
        if _is_business(d, holidays):
            n -= 1
    return d


def deadline_for(received: date, product_kind: str, cfg: dict) -> date:
    if product_kind not in ("payment", "other"):
        raise ValueError(f"unknown product_kind: {product_kind!r}")
    rule = cfg["deadlines"][product_kind]
    if product_kind != "payment":
        return received + timedelta(weeks=rule["weeks"])
    holidays = {date.fromisoformat(d) for d in cfg["bank_holidays"]}
    return add_business_days(received, rule["business_days"], holidays)


def business_days_left(deadline: date, today: date, holidays: set[date]) -> int:
    if isinstance(deadline, datetime) or isinstance(today, datetime):
        raise TypeError("dates only, not datetimes")
    lo, hi, sign = (today, deadline, 1) if deadline >= today else (deadline, today, -1)
    # Counts business days in (lo, hi].
    n = sum(_is_business(lo + timedelta(days=i), holidays) for i in range(1, (hi - lo).days + 1))
    return sign * max(1, n) if sign < 0 else n


def due_soon_edge(today: date, limit: int, holidays: set[date]) -> date:
    """The last deadline date that still has at most `limit` business days left."""
    return add_business_days(today, limit + 1, holidays) - timedelta(days=1)
