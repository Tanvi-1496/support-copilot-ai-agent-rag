"""App state (traces, approvals, feedback). Kept in a separate read-write SQLite file so the
business database can stay strictly read-only."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager

from .config import settings

_lock = threading.Lock()

DDL = """
CREATE TABLE IF NOT EXISTS traces(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, level TEXT, question TEXT, answer TEXT,
  latency_ms INTEGER, tool_calls INTEGER, in_tokens INTEGER, out_tokens INTEGER,
  status TEXT, events TEXT, rating INTEGER);
CREATE TABLE IF NOT EXISTS approvals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, action TEXT, order_id INTEGER, amount REAL,
  reason TEXT, status TEXT DEFAULT 'PENDING', decided_ts REAL, decision_note TEXT, trace_id INTEGER);
"""


@contextmanager
def conn():
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with _lock:
        c = sqlite3.connect(settings.ops_db_path, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            c.executescript(DDL)
            yield c
            c.commit()
        finally:
            c.close()


def log_trace(level, question, answer, latency_ms, tool_calls, in_tok, out_tok, status, events) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO traces(ts,level,question,answer,latency_ms,tool_calls,in_tokens,out_tokens,status,events)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (time.time(), level, question, answer, latency_ms, tool_calls, in_tok, out_tok, status,
             json.dumps(events, default=str)[:200_000]),
        )
        return cur.lastrowid


def list_traces(limit=50):
    with conn() as c:
        rows = c.execute(
            "SELECT id,ts,level,question,latency_ms,tool_calls,in_tokens,out_tokens,status,rating "
            "FROM traces ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_trace(tid: int):
    with conn() as c:
        r = c.execute("SELECT * FROM traces WHERE id=?", (tid,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["events"] = json.loads(d["events"] or "[]")
        return d


def rate_trace(tid: int, rating: int):
    with conn() as c:
        c.execute("UPDATE traces SET rating=? WHERE id=?", (rating, tid))


def trace_stats():
    with conn() as c:
        r = c.execute(
            "SELECT COUNT(*) n, AVG(latency_ms) lat, SUM(in_tokens) it, SUM(out_tokens) ot, "
            "SUM(CASE WHEN status!='ok' THEN 1 ELSE 0 END) errs, "
            "SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) up, SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) down "
            "FROM traces").fetchone()
        return dict(r)


def create_approval(action, order_id, amount, reason, trace_id=None) -> dict:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO approvals(ts,action,order_id,amount,reason,trace_id) VALUES(?,?,?,?,?,?)",
            (time.time(), action, order_id, amount, reason, trace_id))
        return dict(c.execute("SELECT * FROM approvals WHERE id=?", (cur.lastrowid,)).fetchone())


def list_approvals(status: str | None = None):
    with conn() as c:
        if status:
            rows = c.execute("SELECT * FROM approvals WHERE status=? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM approvals ORDER BY id DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]


def decide_approval(aid: int, decision: str, note: str = ""):
    assert decision in {"APPROVED", "REJECTED"}
    with conn() as c:
        c.execute("UPDATE approvals SET status=?, decided_ts=?, decision_note=? WHERE id=? AND status='PENDING'",
                  (decision, time.time(), note, aid))
        r = c.execute("SELECT * FROM approvals WHERE id=?", (aid,)).fetchone()
        return dict(r) if r else None
