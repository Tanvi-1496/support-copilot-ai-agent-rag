import { useEffect, useState } from 'react'
import { api } from '../api'
import TracePanel from '../components/TracePanel.jsx'
import Answer from '../components/Answer.jsx'

const when = (ts) => new Date(ts * 1000).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
const NAMES = { llm: 'LLM', rag: 'RAG', agent: 'Agent', agentic: 'Agentic' }

export default function Traces() {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api('/api/traces').then(setData).catch((e) => setErr(e.message)) }, [])
  const show = (id) => api(`/api/traces/${id}`).then(setOpen).catch((e) => setErr(e.message))

  if (err) return <div className="page"><div className="error-box">{err}</div></div>
  if (!data) return <div className="page"><p className="muted">Loading…</p></div>
  const s = data.stats

  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Run history</h1><p>Every question is stored with its tool trace, latency, token use and your thumbs. This is how you debug an agent after the fact.</p></div>
      </div>
      <div className="kpis">
        <div className="kpi"><span>Runs</span><b>{s.n}</b><small>{s.errs || 0} failed</small></div>
        <div className="kpi"><span>Average latency</span><b>{s.lat ? (s.lat / 1000).toFixed(1) : '—'}s</b></div>
        <div className="kpi"><span>Tokens used</span><b>{((s.it || 0) + (s.ot || 0)).toLocaleString('en-IN')}</b></div>
        <div className="kpi"><span>Feedback</span><b>{s.up || 0} 👍 {s.down || 0} 👎</b></div>
      </div>
      <div className="card scroll-x">
        {data.items.length === 0 ? <p className="empty">No runs yet. Ask something in the Console.</p> : (
          <table className="t">
            <thead><tr><th>When</th><th>Level</th><th>Question</th><th>Tools</th><th>Latency</th><th>Status</th></tr></thead>
            <tbody>
              {data.items.map((t) => (
                <tr key={t.id} className="click" tabIndex={0} onClick={() => show(t.id)} onKeyDown={(e) => e.key === 'Enter' && show(t.id)}>
                  <td>{when(t.ts)}</td><td>{NAMES[t.level] || t.level}</td><td style={{ maxWidth: 420 }}>{t.question}</td>
                  <td>{t.tool_calls}</td><td>{(t.latency_ms / 1000).toFixed(1)}s</td>
                  <td><span className={`pill ${t.status === 'ok' ? '' : 'bad'}`}>{t.status}</span> {t.rating === 1 && '👍'}{t.rating === -1 && '👎'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {open && (
        <div className="grid2" style={{ marginTop: 16 }}>
          <div className="card"><h3>Q: {open.question}</h3><div className="bubble" style={{ marginTop: 10 }}><Answer text={open.answer || ''} /></div></div>
          <TracePanel events={open.events} final={{ latency_ms: open.latency_ms, tool_calls: open.tool_calls, usage: { in: open.in_tokens, out: open.out_tokens } }} title={`Trace #${open.id}`} />
        </div>
      )}
    </div>
  )
}
