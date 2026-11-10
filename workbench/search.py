import re
import sqlite3


def _fts_query(q: str, joiner: str) -> str:
    # Each whitespace-separated token becomes one quoted phrase, so FTS operators and punctuation are inert.
    toks = [t.replace('"', " ") for t in q.split() if re.search(r"\w", t)]
    return f" {joiner} ".join(f'"{t}"' for t in toks)


def search_policies(conn: sqlite3.Connection, q: str, k: int = 5) -> list[sqlite3.Row]:
    sql = ("SELECT p.id, p.section, p.title, snippet(policies_fts, 2, '', '', '...', 20) AS snippet,"
           " bm25(policies_fts, 10.0, 3.0, 1.0) AS rank"
           " FROM policies_fts JOIN policies p ON p.id = policies_fts.id"
           " WHERE policies_fts MATCH ? ORDER BY rank LIMIT ?")
    if not _fts_query(q, "AND"):
        return conn.execute("SELECT id, section, title, substr(body, 1, 160) AS snippet, 0.0 AS rank"
                            " FROM policies ORDER BY id LIMIT ?", (k,)).fetchall()
    # All words first; a long complaint text rarely matches every word, so fall back to any word.
    rows = conn.execute(sql, (_fts_query(q, "AND"), k)).fetchall()
    if rows:
        return rows
    fts = _fts_query(q, "OR")
    return conn.execute(sql, (fts, k)).fetchall() if fts else []
