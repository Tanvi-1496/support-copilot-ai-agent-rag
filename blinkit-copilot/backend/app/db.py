"""Read-only access to the Blinkit operations database.

Three independent layers keep LLM-written SQL safe:
  1. the file is opened with mode=ro (SQLite itself refuses writes)
  2. a SQLite *authorizer* only allows SELECT / READ / harmless functions
  3. a progress handler kills any query that runs longer than the timeout
"""
from __future__ import annotations

import re
import sqlite3
import time
from functools import lru_cache

from .config import settings

_OK = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    getattr(sqlite3, "SQLITE_RECURSIVE", 33),
}
_BAD_FUNCS = {"load_extension", "readfile", "writefile", "edit"}


class SQLRejected(Exception):
    pass


def _authorizer(action, arg1, arg2, db_name, source):
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in _BAD_FUNCS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK if action in _OK else sqlite3.SQLITE_DENY


def validate_sql(sql: str) -> str:
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise SQLRejected("Empty query.")
    if ";" in s:
        raise SQLRejected("Only one statement is allowed.")
    if not re.match(r"^(select|with)\b", s, re.I):
        raise SQLRejected("Only SELECT queries are allowed.")
    return s


def connect_readonly() -> sqlite3.Connection:
    if not settings.db_path.exists():
        raise FileNotFoundError(f"Database not found at {settings.db_path}")
    con = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True, timeout=5, check_same_thread=False)
    con.execute("PRAGMA query_only = ON")
    con.set_authorizer(_authorizer)
    return con


def run_readonly(sql: str, limit: int | None = None, params: tuple = ()) -> tuple[list[str], list[tuple], bool]:
    """Returns (columns, rows, truncated). Raises SQLRejected / sqlite3.Error."""
    limit = limit or settings.sql_row_limit
    s = validate_sql(sql)
    con = connect_readonly()
    deadline = time.monotonic() + settings.sql_timeout_s
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 20000)
    try:
        cur = con.execute(s, params)
        cols = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(limit + 1)
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e).lower():
            raise SQLRejected(f"Query took longer than {settings.sql_timeout_s}s. Add filters or LIMIT.") from e
        raise
    finally:
        con.close()
    return cols, rows[:limit], len(rows) > limit


def rows_as_dicts(sql: str, params: tuple = (), limit: int = 500) -> list[dict]:
    cols, rows, _ = run_readonly(sql, limit=limit, params=params)
    return [dict(zip(cols, r)) for r in rows]


def format_table(cols: list[str], rows: list[tuple], truncated: bool = False) -> str:
    if not rows:
        return "No rows found."
    data = [[("" if v is None else str(v)) for v in r] for r in rows]
    widths = [max(len(c), *(len(r[i]) for r in data)) for i, c in enumerate(cols)]
    line = lambda r: " | ".join(v.ljust(widths[i]) for i, v in enumerate(r))
    out = [line(cols), "-+-".join("-" * w for w in widths), *(line(r) for r in data)]
    if truncated:
        out.append(f"... (showing first {len(rows)} rows; refine the query for more)")
    return "\n".join(out)


@lru_cache(maxsize=1)
def schema_text() -> str:
    """CREATE statements + row counts. Injected into agent prompts so SQL is grounded in the real schema."""
    con = connect_readonly()
    try:
        tables = con.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        parts = []
        for name, sql in tables:
            n = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            parts.append(f"-- {name}: {n:,} rows\n{sql};")
        return "\n\n".join(parts)
    finally:
        con.close()


def db_ready() -> bool:
    return settings.db_path.exists()
