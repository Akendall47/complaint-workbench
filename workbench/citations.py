import unicodedata

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", s).translate(_QUOTES).split()).casefold()


def quote_in_source(quote: str, source: str) -> bool:
    q = _norm(quote)
    return len(q) >= 12 and q in _norm(source)
