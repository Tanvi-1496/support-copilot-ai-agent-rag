# Support Copilot

An AI support and operations assistant for a quick-commerce business (Blinkit-style): customers' refund questions, policy rules and ops analytics, answered by four levels of AI that you can compare side by side.

It grows the "LLM → RAG → Agent → Agentic AI" notebook into a deployable product: real API, streaming UI, hybrid retrieval, guarded SQL, human approvals, run history and an eval suite.

```
React + Vite UI ──SSE──▶ FastAPI ──▶ agents.py ──▶ Gemini (generate + embed)
 Console · Operations      │            │  tools.py: policy_search · run_sql · get_order_summary
 Approvals · Run history   │            │            web_search · propose_action
                           │            └─ rag.py: PDF → chunks → BM25 + vectors → RRF
                           ├─ db.py   read-only SQLite (mode=ro + authorizer + timeout)
                           └─ ops.py  traces, approvals, feedback (separate read-write file)
```

## What is new compared to the notebook

| Notebook | This project |
|---|---|
| In-memory vector store, rebuilt every run | Persisted index, heading-aware chunks with page and section, **hybrid search** (BM25 + embeddings, Reciprocal Rank Fusion). Falls back to BM25 if embeddings are unavailable |
| `startswith("select")` check | SQLite opened read-only, authorizer allows only SELECT/READ, one statement, 5 s timeout, 50 row cap. Tested against DROP/DELETE/ATTACH/PRAGMA/runaway queries |
| Agent could only read | `propose_action` queues wallet credits, escalations and store warnings for a **human**. Approvals page is the control point. Nothing executes automatically |
| Supervisor and sub-agents via a library | Own small tool loop: step budget, tool-crash isolation, unknown-tool handling, forced final answer when out of steps. Easy to read and unit test |
| Output in a notebook cell | Streaming trace in the UI: plan, delegated specialist lanes, SQL, retrieved passages with page numbers, latency, tokens |
| No history | Every run stored with trace and thumbs up/down. Operations dashboard shows the numbers the agents query |
| Manual test prompts | `pytest` (36 tests, no API key needed) and `evals/` that check tools used, facts present and refusals |
| Prompt injection not considered | Tool output is treated as data in every system prompt. SQL and actions are bounded as above |

## Run it locally

```bash
# 1. backend
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # add GOOGLE_API_KEY (and optionally TAVILY_API_KEY)
uvicorn app.main:app --reload --port 8000

# 2. frontend (new terminal)
cd frontend
npm install
npm run dev                                              # http://localhost:5173
```

First boot creates demo data (`data/blinkit.db`, `data/policy.pdf`) and the search index. No API key? Everything except answers works: dashboard, policy search, SQL guard, approvals.

**Use your own data:** copy your `blinkit.db` and policy PDF to `backend/data/` as `blinkit.db` and `policy.pdf` (or set `BLINKIT_DB`, `POLICY_PDF`), delete `backend/data/index/`, restart. The agents read the live schema, so they adapt. The dashboard and `get_order_summary` use fixed column names; if yours differ, edit only `backend/app/queries.py`.

## Test and evaluate

```bash
cd backend
python -m pytest -q              # guard, retrieval, agent loop (scripted fake model), API
python -m evals.run_evals        # needs GOOGLE_API_KEY: real model, checks tools + facts + refusals
```

## Deploy

**Backend → Render** (or Railway/Fly): push to GitHub, New → Blueprint, pick the repo (`render.yaml`). Set `GOOGLE_API_KEY`, `TAVILY_API_KEY` and `CORS_ORIGINS` (your Vercel URL). Health check is `/api/health`.

**Frontend → Vercel**: import the repo, root directory `frontend`, env `VITE_API_URL=https://<your-render-service>.onrender.com`. Add that Vercel URL to the backend's `CORS_ORIGINS`.

**Anywhere with Docker:** `docker compose up --build` then open http://localhost:8080 (nginx serves the UI and proxies `/api` with buffering off so streaming works).

Free-tier note: Render's free disk is ephemeral, so traces and approvals reset on redeploy and the index is rebuilt at boot. For a real deployment move `ops.db` to Postgres and mount a persistent volume for `data/`.

## Production checklist (what this demo deliberately leaves out)

- Real authentication (SSO/JWT) and per-user roles for the Approvals page. `APP_API_KEY` is only a shared demo gate
- Executing approved actions: wire the payments or ticketing API into `decide()` in `app/main.py`, with the approver's identity
- PII handling: masking customer names in prompts and logs, retention policy for traces
- A real reranker on top of hybrid retrieval, and a larger eval set built from real tickets
- Metrics and alerts (latency, error rate, token cost) in your observability stack

## Layout

```
backend/app/    main.py (API+SSE) agents.py (4 levels) tools.py rag.py db.py ops.py llm.py queries.py analytics.py
backend/scripts/  bootstrap.py make_demo_data.py        backend/tests/   backend/evals/
frontend/src/   pages/ (Console, Operations, Approvals, Traces)  components/TracePanel.jsx
```

The bundled data is synthetic and for demonstration only.
