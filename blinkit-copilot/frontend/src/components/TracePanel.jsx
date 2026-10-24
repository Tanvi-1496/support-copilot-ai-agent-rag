import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, AlertCircle, Clock, ChevronDown, ChevronRight, UserCheck, ShieldAlert, Cpu } from 'lucide-react'

const TONE = {
  policy_search: 'tone-policy',
  run_sql: 'tone-sql',
  web_search: 'tone-web',
  get_order_summary: 'tone-order',
  propose_action: 'tone-act',
  write_plan: 'tone-plan',
  delegate: 'tone-delegate',
}

/** Turn the flat event stream into a render list: plan blocks, delegate groups, merged call+result steps. */
export function buildSteps(events) {
  const out = []
  const byId = {}
  const delegates = []
  let depth = 0

  for (const e of events) {
    if (e.type === 'plan') {
      out.push({ kind: 'plan', steps: e.steps, depth })
    } else if (e.type === 'delegate') {
      const d = {
        kind: 'delegate',
        id: e.id || `del_${out.length}`,
        agent: e.agent,
        task: e.task,
        depth,
        status: 'running',
        result: null,
      }
      delegates.push(d)
      out.push(d)
      depth += 1
    } else if (e.type === 'delegate_done') {
      let matched = null
      if (e.id) {
        matched = delegates.slice().reverse().find((d) => d.id === e.id)
      }
      if (!matched && e.agent) {
        matched = delegates.slice().reverse().find((d) => d.agent === e.agent && d.status === 'running')
      }
      if (matched) {
        matched.status = e.ok === false ? 'failed' : 'completed'
        matched.result = e
      }
      depth = Math.max(0, depth - 1)
    } else if (e.type === 'tool_call') {
      if (e.name === 'delegate' || e.name === 'write_plan') continue // represented by dedicated blocks
      const s = {
        kind: 'step',
        id: e.id,
        name: e.name,
        args: e.args,
        agent: e.agent,
        depth,
        status: 'running',
        result: null,
      }
      byId[e.id] = s
      out.push(s)
    } else if (e.type === 'tool_result') {
      if (byId[e.id]) {
        byId[e.id].result = e
        byId[e.id].status = e.ok ? 'completed' : 'failed'
      }
    } else if (e.type === 'approval') {
      out.push({ kind: 'approval', approval: e.approval, depth })
    }
  }
  return out
}

function brief(name, args) {
  if (!args) return ''
  if (name === 'run_sql') return (args.sql || '').replace(/\s+/g, ' ')
  if (name === 'get_order_summary') return `order #${args.order_id}`
  if (name === 'propose_action') return `${args.action} · order #${args.order_id} · ₹${args.amount}`
  if (name === 'policy_search') return `"${args.query || ''}"`
  if (name === 'web_search') return `"${args.query || ''}"`
  return args.query || JSON.stringify(args)
}

function Step({ s }) {
  const r = s.result
  const isPending = s.status === 'running' || !r
  const isFailed = s.status === 'failed' || (r && !r.ok)
  const isSuccess = s.status === 'completed' || (r && r.ok)

  const statusClass = isPending ? 'pending' : isFailed ? 'fail' : 'ok'

  return (
    <details className={`step ${statusClass} ${TONE[s.name] || ''}`}>
      <summary>
        <span className="step-status-icon" aria-hidden="true">
          {isPending && <i className="st st-pending" title="Running..." />}
          {isSuccess && <i className="st st-ok" title="Successful" />}
          {isFailed && <i className="st st-fail" title="Failed" />}
        </span>
        <span className="nm">{s.name}</span>
        {s.agent && s.agent !== 'agent' && <span className="agent-badge">{s.agent}</span>}
        <span className="arg">{brief(s.name, s.args)}</span>
        <span className="ms">
          {isPending ? (
            <span className="time-badge running">running…</span>
          ) : (
            <span className={`time-badge ${isFailed ? 'failed' : ''}`}>{r?.ms ?? 0} ms</span>
          )}
        </span>
      </summary>
      <div className="detail">
        {s.name === 'run_sql' && s.args?.sql && (
          <div className="detail-section">
            <span className="detail-label">Executed SQL Query:</span>
            <pre className="code-block">{s.args.sql}</pre>
          </div>
        )}
        {r?.ui?.sources?.length > 0 && (
          <div className="src">
            <span className="detail-label">Retrieved Policy Passages ({r.ui.mode || 'hybrid'}):</span>
            {r.ui.sources.map((x, i) => (
              <div key={i} className="src-item">
                <div className="src-header">
                  <span className="badge-page">Page {x.page}</span>
                  <span className="src-section">{x.section}</span>
                  {x.score != null && <span className="src-score">score: {Number(x.score).toFixed(2)}</span>}
                </div>
                <p className="src-snippet">{x.snippet}…</p>
              </div>
            ))}
          </div>
        )}
        {r?.ui?.error && (
          <div className="trace-error-box">
            <b>Tool Error:</b> {r.ui.error}
          </div>
        )}
        {r?.preview && (
          <div className="detail-section">
            <span className="detail-label">Tool Output Preview:</span>
            <pre className="code-block">{r.preview}</pre>
          </div>
        )}
        {isPending && <span className="muted detail-waiting">Awaiting tool execution result…</span>}
      </div>
    </details>
  )
}

function DelegateBlock({ it }) {
  const [open, setOpen] = useState(false)
  const isRunning = it.status === 'running'
  const isFailed = it.status === 'failed'
  const isSuccess = it.status === 'completed'
  const r = it.result

  return (
    <div className={`delegate-block ${isRunning ? 'running' : isFailed ? 'failed' : 'completed'}`}>
      <div className="delegate-header">
        <div className="delegate-title">
          <Cpu size={15} className="delegate-icon" aria-hidden="true" />
          <span>Delegated to Specialist Worker:</span>
          <b>{it.agent}</b>
        </div>
        <div className="delegate-meta">
          {isRunning && <span className="pill warn">Worker active…</span>}
          {isSuccess && <span className="pill ok">{r?.ms ? `${r.ms} ms` : 'Done'}</span>}
          {isFailed && <span className="pill bad">Worker error</span>}
          {r?.output && (
            <button
              type="button"
              className="btn-tiny"
              onClick={() => setOpen(!open)}
              aria-expanded={open}
            >
              {open ? 'Hide result' : 'View result'}
            </button>
          )}
        </div>
      </div>
      <div className="delegate-task">
        <span className="delegate-task-label">Subtask:</span> {it.task}
      </div>
      {open && r && (
        <div className="delegate-result-drawer">
          <span className="detail-label">Specialist Findings / Report:</span>
          <pre className="code-block">{r.output || r.preview}</pre>
        </div>
      )}
    </div>
  )
}

function Block({ it }) {
  if (it.kind === 'plan') {
    return (
      <div className="plan">
        <div className="plan-header">
          <span className="plan-title">Supervisor Orchestration Plan</span>
          <span className="plan-count">{it.steps.length} sequential steps</span>
        </div>
        <ol className="plan-steps">
          {it.steps.map((x, i) => (
            <li key={i}>{x}</li>
          ))}
        </ol>
      </div>
    )
  }
  if (it.kind === 'delegate') {
    return <DelegateBlock it={it} />
  }
  if (it.kind === 'approval') {
    const a = it.approval
    return (
      <div className="approval-card">
        <div className="approval-card-head">
          <ShieldAlert size={16} aria-hidden="true" />
          <b>Human Approval Required:</b>
        </div>
        <p className="approval-card-body">
          {a.action ? a.action.replace(/_/g, ' ') : 'ACTION'} for order #{a.order_id}
          {a.amount > 0 && <> · ₹{a.amount}</>} queued for human decision. Nothing was executed automatically.
        </p>
        <Link to="/approvals" className="approval-card-link">Review pending approvals &rarr;</Link>
      </div>
    )
  }
  return <Step s={it} />
}

function Tree({ items }) {
  const rows = []
  let i = 0
  const walk = (depth) => {
    const nodes = []
    while (i < items.length) {
      const it = items[i]
      if (it.depth < depth) break
      if (it.depth > depth) {
        nodes.push(
          <div className="nest" key={`n${i}`}>
            {walk(it.depth)}
          </div>
        )
        continue
      }
      nodes.push(<Block it={it} key={i} />)
      i += 1
    }
    return nodes
  }
  rows.push(...walk(0))
  return <div className="steps">{rows}</div>
}

export default function TracePanel({ events, running, final, title = 'Execution Trace & Observability' }) {
  const items = useMemo(() => buildSteps(events), [events])

  return (
    <section className="trace" aria-label="Run trace">
      <div className="trace-head">
        <div className="trace-head-title">
          <h3>{title}</h3>
          {items.length > 0 && (
            <span className="trace-count-badge">
              {items.filter((x) => x.kind === 'step').length} calls
            </span>
          )}
        </div>
        {running && (
          <div className="trace-running-indicator">
            <span className="thinking" aria-label="Executing">
              <i /><i /><i />
            </span>
            <span className="running-text">Running workflow…</span>
          </div>
        )}
      </div>

      <div className="trace-body">
        {items.length === 0 && !running ? (
          <div className="trace-empty">
            <p className="trace-empty-intro">
              Inspect real-time execution steps, tool invocations, SQL queries, and retrieved passages.
            </p>
            <div className="trace-level-guides">
              <div className="guide-item">
                <span className="guide-name">1. LLM</span>
                <span className="guide-desc">Pure parametric memory; no external tool calls.</span>
              </div>
              <div className="guide-item">
                <span className="guide-name">2. RAG</span>
                <span className="guide-desc">Single retrieval step grounded in Policy PDF, Database, or Web.</span>
              </div>
              <div className="guide-item">
                <span className="guide-name">3. AI Agent</span>
                <span className="guide-desc">Autonomous tool loop dynamically selecting tools toward a goal.</span>
              </div>
              <div className="guide-item">
                <span className="guide-name">4. Agentic AI</span>
                <span className="guide-desc">Supervisor creates an execution plan, coordinates specialized workers, and synthesizes results.</span>
              </div>
            </div>
          </div>
        ) : (
          <Tree items={items} />
        )}
        {items.length === 0 && running && (
          <div className="trace-initializing">
            <span className="thinking"><i /><i /><i /></span>
            <p className="muted">Initializing workflow and preparing agent execution…</p>
          </div>
        )}
      </div>

      {final && (
        <div className="trace-foot">
          <div className="trace-metric">
            <span className="metric-label">Latency:</span>
            <span className="metric-value">{(final.latency_ms / 1000).toFixed(2)}s</span>
          </div>
          <div className="trace-metric">
            <span className="metric-label">Tool Calls:</span>
            <span className="metric-value">{final.tool_calls}</span>
          </div>
          <div className="trace-metric">
            <span className="metric-label">Token Usage:</span>
            <span className="metric-value">
              {((final.usage?.in || 0) + (final.usage?.out || 0)).toLocaleString('en-IN')} tok
              <span className="token-split">({final.usage?.in || 0} in / {final.usage?.out || 0} out)</span>
            </span>
          </div>
        </div>
      )}
    </section>
  )
}
