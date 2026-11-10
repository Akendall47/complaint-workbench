def _norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def quote_in_source(quote: str, source: str) -> bool:
    q = _norm(quote)
    return len(q) >= 12 and q in _norm(source)
