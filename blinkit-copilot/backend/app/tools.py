"""Tools the agents can call. Each returns (text_for_llm, ui_payload_for_trace_panel).

Design rules: tools are read-only except propose_action, which only *queues* a request for a
human. The agent can never move money."""
from __future__ import annotations

import sqlite3

import httpx

from . import db, ops, queries
from .config import settings
from .llm import ToolSpec
from .rag import PolicyIndex, format_hits

_index: PolicyIndex | None = None
_trace_id: dict = {"current": None}  # set by the API layer so approvals link back to the run


def set_index(idx: PolicyIndex | None):
    global _index
    _index = idx


def get_index() -> PolicyIndex | None:
    return _index


ACTIONS = {"WALLET_CREDIT", "ESCALATE_TICKET", "STORE_WARNING"}


def policy_search(args: dict):
    q = str(args.get("query", "")).strip()
    if not _index:
        return "Policy index is not built yet.", {"sources": []}
    hits = _index.search(q, k=4)
    ui = {"mode": _index.mode, "sources": [
        {"page": h.chunk.page, "section": h.chunk.section, "score": h.score, "snippet": h.chunk.text[:220]} for h in hits]}
    return format_hits(hits), ui


def run_sql(args: dict):
    sql = str(args.get("sql", ""))
    try:
        cols, rows, trunc = db.run_readonly(sql)
    except db.SQLRejected as e:
        return f"Rejected: {e}", {"sql": sql, "error": str(e)}
    except (sqlite3.Error, FileNotFoundError) as e:
        return f"SQL error: {e}. Check the schema and try again.", {"sql": sql, "error": str(e)}
    return db.format_table(cols, rows, trunc), {"sql": sql, "rows": len(rows), "truncated": trunc}


def web_search(args: dict):
    q = str(args.get("query", "")).strip()
    if not settings.tavily_api_key:
        return "Web search is not configured (TAVILY_API_KEY missing).", {"error": "not configured"}
    try:
        r = httpx.post("https://api.tavily.com/search", timeout=15,
                       json={"api_key": settings.tavily_api_key, "query": q, "max_results": 3})
        r.raise_for_status()
        res = r.json().get("results", [])
    except Exception as e:
        return f"Web search failed: {e}", {"error": str(e)}
    text = "\n\n".join(f"{x['title']}\n{x['content']}\n{x['url']}" for x in res) or "No web results."
    return text, {"urls": [x["url"] for x in res]}


def get_order_summary(args: dict):
    try:
        oid = int(args.get("order_id"))
    except (TypeError, ValueError):
        return "order_id must be an integer.", {"error": "bad id"}
    try:
        o = db.rows_as_dicts(queries.ORDER, (oid,))
        if not o:
            return f"No order with id {oid}.", {"order_id": oid, "found": False}
        o = o[0]
        items = db.rows_as_dicts(queries.ITEMS, (oid,))
        refunds = db.rows_as_dicts(queries.REFUNDS, (oid,))
        tickets = db.rows_as_dicts(queries.TICKETS, (oid,))
    except Exception as e:
        return f"Order lookup failed: {e}", {"error": str(e)}

    def block(title, rows):
        if not rows:
            return f"{title}: none"
        return f"{title}:\n" + "\n".join("  - " + ", ".join(f"{k}={v}" for k, v in r.items()) for r in rows)

    head = ", ".join(f"{k}={v}" for k, v in o.items())
    text = "\n".join([f"ORDER: {head}", block("ITEMS", items), block("REFUNDS", refunds), block("TICKETS", tickets)])
    return text, {"order_id": oid, "found": True, "late_by": o["minutes_late"], "tier": o["customer_tier"],
                  "items": len(items), "refunds": len(refunds)}


def propose_action(args: dict):
    action = str(args.get("action", "")).upper()
    if action not in ACTIONS:
        return f"Unknown action. Allowed: {sorted(ACTIONS)}", {"error": "bad action"}
    try:
        order_id = int(args.get("order_id"))
        amount = float(args.get("amount", 0) or 0)
    except (TypeError, ValueError):
        return "order_id and amount must be numbers.", {"error": "bad args"}
    if amount < 0 or amount > 2000:
        return "Amount must be between 0 and 2000. Larger amounts need a manager outside this tool.", {"error": "limit"}
    row = ops.create_approval(action, order_id, amount, str(args.get("reason", ""))[:500], _trace_id["current"])
    return (f"Request #{row['id']} queued for HUMAN approval ({action}, order {order_id}, INR {amount:g}). "
            "It has NOT been executed. Tell the user it is pending approval."), {"approval": row}


def write_plan(args: dict):
    raw_steps = args.get("steps") or []
    if isinstance(raw_steps, str):
        steps = [s.strip().lstrip("0123456789.- ") for s in raw_steps.split("\n") if s.strip()]
    elif isinstance(raw_steps, (list, tuple)):
        steps = [str(s).strip() for s in raw_steps if str(s).strip()]
    else:
        steps = [str(raw_steps).strip()] if str(raw_steps).strip() else []

    if not steps:
        return "Plan was empty. Please provide 2-5 clear sequential steps.", {"steps": [], "error": "empty plan"}
    return f"Plan recorded with {len(steps)} steps. Proceed to delegate each step to specialist workers.", {"steps": steps}


S = lambda **kw: {"type": "OBJECT", "properties": kw, "required": list(kw)}
STR = lambda d: {"type": "STRING", "description": d}

TOOLS: dict[str, ToolSpec] = {t.name: t for t in [
    ToolSpec("policy_search",
             "Search the Blinkit Ordering, Delivery and Refunds policy. Use for rules, fees, the 10-minute promise, "
             "refund timelines, weight tolerance, Gold benefits, goodwill bands, escalation, conduct rules. "
             "Returns passages tagged with page numbers.",
             S(query=STR("What to look up, in plain words")), policy_search),
    ToolSpec("run_sql",
             "Run ONE read-only SQLite SELECT against the Blinkit operations database (orders, order_items, refunds, "
             "support_tickets, dark_stores, customers, products, inventory, cities, delivery_partners, reviews). "
             "Max 50 rows returned. Prefer aggregates over raw rows.",
             S(sql=STR("A single SELECT statement")), run_sql),
    ToolSpec("get_order_summary",
             "Fetch one order with its customer tier, minutes late, line items, refunds and tickets in one call. "
             "Use this first for any question about a specific order id.",
             S(order_id={"type": "INTEGER", "description": "Order id"}), get_order_summary),
    ToolSpec("web_search",
             "Search the live web for external or current information (competitor fees, news, regulation). "
             "Not for Blinkit's own orders or policy.",
             S(query=STR("Search query")), web_search),
    ToolSpec("propose_action",
             "Queue a request for a HUMAN to approve: WALLET_CREDIT, ESCALATE_TICKET or STORE_WARNING. "
             "This never executes anything. Only call it when policy clearly supports the action.",
             {"type": "OBJECT", "properties": {
                 "action": {"type": "STRING", "description": "WALLET_CREDIT | ESCALATE_TICKET | STORE_WARNING"},
                 "order_id": {"type": "INTEGER", "description": "Related order id"},
                 "amount": {"type": "NUMBER", "description": "INR amount (0 if not money)"},
                 "reason": {"type": "STRING", "description": "Why, citing the policy page"}},
              "required": ["action", "order_id", "amount", "reason"]}, propose_action),
    ToolSpec("write_plan",
             "Supervisor only. Record the numbered plan before delegating.",
             {"type": "OBJECT", "properties": {"steps": {"type": "ARRAY", "items": {"type": "STRING"},
                                                          "description": "Ordered steps"}},
              "required": ["steps"]}, write_plan),
]}

DELEGATE = ToolSpec(
    "delegate",
    "Hand one focused task to a specialist: refund-agent (refund backlog, eligibility, policy), "
    "quality-agent (stores, cities, SKUs, delivery patterns), comms-agent (customer/store messages). "
    "Include every fact and number the specialist needs; it cannot see this conversation.",
    {"type": "OBJECT", "properties": {
        "agent": {"type": "STRING", "description": "refund-agent | quality-agent | comms-agent"},
        "task": {"type": "STRING", "description": "Self-contained task description"}},
     "required": ["agent", "task"]})
