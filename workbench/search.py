import re
import sqlite3

from markupsafe import Markup, escape


def _fts_query(q: str, joiner: str) -> str:
    # Each whitespace-separated token becomes one quoted phrase, so FTS operators and punctuation are inert.
    toks = [t.replace('"', " ") for t in q.replace("\x00", " ").split()[:50] if re.search(r"\w", t)]
    return f" {joiner} ".join(f'"{t}"' for t in toks)


def search_policies(conn: sqlite3.Connection, q: str, k: int = 5, sections: list[str] | None = None) -> list[sqlite3.Row]:
    marks = ",".join("?" * len(sections)) if sections else ""
    where = f" AND p.section IN ({marks})" if sections else ""
    extra = list(sections or [])
    sql = ("SELECT p.id, p.section, p.title, snippet(policies_fts, 2, '', '', '...', 20) AS snippet,"
           " bm25(policies_fts, 10.0, 3.0, 1.0) AS rank"
           " FROM policies_fts JOIN policies p ON p.id = policies_fts.id"
           f" WHERE policies_fts MATCH ?{where} ORDER BY rank LIMIT ?")
    if not _fts_query(q, "AND"):
        return conn.execute("SELECT p.id, p.section, p.title, substr(p.body, 1, 160) AS snippet, 0.0 AS rank"
                            f" FROM policies p WHERE 1=1{where} ORDER BY id LIMIT ?", (*extra, k)).fetchall()
    # All words first; a long complaint text rarely matches every word, so fall back to any word.
    rows = conn.execute(sql, (_fts_query(q, "AND"), *extra, k)).fetchall()
    if rows:
        return rows
    fts = _fts_query(q, "OR")
    return conn.execute(sql, (fts, *extra, k)).fetchall() if fts else []


def highlight(text: str, q: str) -> Markup:
    """The text escaped, with the query words wrapped in <mark>. Each piece is escaped before any markup is added."""
    words = sorted({w for w in q.split() if re.search(r"\w", w)}, key=len, reverse=True)[:20]
    if not words:
        return Markup(escape(text))
    parts = re.split("(" + "|".join(re.escape(w) for w in words) + ")", text, flags=re.I)
    return Markup("".join(f"<mark>{escape(p)}</mark>" if i % 2 else str(escape(p)) for i, p in enumerate(parts)))
