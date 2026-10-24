"""FastAPI app. Streams agent events over Server-Sent Events."""
from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import agents, analytics, db, ops, tools
from .config import settings
from .llm import llm
from .rag import load_index

@asynccontextmanager
async def lifespan(_app):
    if settings.auto_bootstrap:
        from scripts.bootstrap import bootstrap
        bootstrap()
    tools.set_index(load_index(embed_query=llm.embed_query if llm.available else None))
    yield


app = FastAPI(title="Blinkit Support Copilot", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


def auth(x_api_key: str | None = Header(default=None)):
    if settings.app_api_key and x_api_key != settings.app_api_key:
        raise HTTPException(401, "Invalid or missing X-API-Key")


_hits: dict[str, deque] = defaultdict(deque)
_rl_lock = threading.Lock()


def rate_limit(request: Request):
    ip = request.client.host if request.client else "?"
    now = time.time()
    with _rl_lock:
        q = _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= settings.rate_limit_per_min:
            raise HTTPException(429, "Too many requests. Slow down a little.")
        q.append(now)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    level: str = "agent"
    source: str = "policy"
    history: list[dict] = []


@app.get("/api/health")
def health():
    idx = tools.get_index()
    return {"status": "ok", "llm_configured": llm.available, "web_search_configured": bool(settings.tavily_api_key),
            "model": settings.model, "database": db.db_ready(),
            "index": {"chunks": len(idx.chunks) if idx else 0, "mode": idx.mode if idx else None}}


@app.post("/api/chat", dependencies=[Depends(auth), Depends(rate_limit)])
def chat(body: ChatIn):
    def stream():
        events, final = [], {}
        tid_holder = {"id": None}
        for ev in agents.run(body.level, body.message, body.history, body.source):
            if ev["type"] in {"final", "error"}:
                final = ev
                tid = ops.log_trace(
                    body.level, body.message, ev.get("text") or ev.get("message", ""), ev.get("latency_ms", 0),
                    ev.get("tool_calls", 0), ev.get("usage", {}).get("in", 0), ev.get("usage", {}).get("out", 0),
                    "ok" if ev["type"] == "final" else "error", events)
                ev["trace_id"] = tid
            else:
                events.append(ev)
            yield f"data: {json.dumps(ev, default=str)}\n\n"
        yield "data: {\"type\":\"done\"}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/analytics/overview", dependencies=[Depends(auth)])
def overview():
    if not db.db_ready():
        raise HTTPException(503, "Database not loaded")
    return analytics.overview()


@app.get("/api/orders/{order_id}", dependencies=[Depends(auth)])
def order(order_id: int):
    text, ui = tools.get_order_summary({"order_id": order_id})
    if not ui.get("found"):
        raise HTTPException(404, text)
    return {"summary": text, **ui}


@app.get("/api/policy/search", dependencies=[Depends(auth)])
def policy_search(q: str, k: int = 4):
    idx = tools.get_index()
    if not idx:
        raise HTTPException(503, "Policy index not built")
    return {"mode": idx.mode, "hits": [
        {"page": h.chunk.page, "section": h.chunk.section, "score": h.score, "via": h.via, "text": h.chunk.text}
        for h in idx.search(q, k=min(k, 8))]}


@app.get("/api/approvals", dependencies=[Depends(auth)])
def approvals(status: str | None = None):
    return ops.list_approvals(status)


class Decision(BaseModel):
    decision: str
    note: str = ""


@app.post("/api/approvals/{aid}/decision", dependencies=[Depends(auth)])
def decide(aid: int, body: Decision):
    d = body.decision.upper()
    if d not in {"APPROVED", "REJECTED"}:
        raise HTTPException(400, "decision must be APPROVED or REJECTED")
    row = ops.decide_approval(aid, d, body.note)
    if not row:
        raise HTTPException(404, "Approval not found")
    # NOTE: this is the integration point. Approving only records the decision; a real deployment
    # would call the payments / ticketing API here, with the approver's identity attached.
    return row


@app.get("/api/traces", dependencies=[Depends(auth)])
def traces():
    return {"stats": ops.trace_stats(), "items": ops.list_traces()}


@app.get("/api/traces/{tid}", dependencies=[Depends(auth)])
def trace(tid: int):
    t = ops.get_trace(tid)
    if not t:
        raise HTTPException(404, "Trace not found")
    return t


class Rating(BaseModel):
    rating: int = Field(ge=-1, le=1)


@app.post("/api/traces/{tid}/feedback", dependencies=[Depends(auth)])
def feedback(tid: int, body: Rating):
    ops.rate_trace(tid, body.rating)
    return {"ok": True}
