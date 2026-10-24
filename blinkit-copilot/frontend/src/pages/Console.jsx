import { useEffect, useRef, useState } from 'react'
import { ThumbsUp, ThumbsDown, Send, Square, CheckCircle2, Info, AlertTriangle, ArrowRight, Sparkles } from 'lucide-react'
import { post, streamChat } from '../api'
import TracePanel from '../components/TracePanel.jsx'
import Answer from '../components/Answer.jsx'

const LEVELS = [
  {
    id: 'llm',
    name: 'LLM',
    tagline: 'Parametric Language Model',
    can: 'Understands language & answers from pretrained memory',
    boundary: 'Parametric memory only: cannot query live databases, orders, or policies',
    starters: [
      'What is the difference between a handling fee and a delivery fee?',
      'Where is my refund for order 10245?',
      'Rewrite politely: "Ten minutes my foot. Forty minutes and the eggs are broken."',
    ],
  },
  {
    id: 'rag',
    name: 'RAG',
    tagline: 'Retrieval-Augmented',
    can: 'Retrieves relevant passages from one selected data source',
    boundary: 'Single retrieval step: cannot chain multiple tools or take actions',
    starters: [
      'How long does a card refund take to reach my bank account?',
      'My 500 g pack of tomatoes weighed 420 g. What am I owed?',
      'What are the three escalation stages and how long does each take?',
    ],
  },
  {
    id: 'agent',
    name: 'AI Agent',
    tagline: 'Autonomous Single-Agent',
    can: 'Dynamically selects and chains tools to solve a specific goal',
    boundary: 'Single-agent execution: multi-agent team delegation requires Level 4',
    starters: [
      'Order 10245 was delivered late and one item was missing. Tell the customer where each refund stands.',
      'A Gold member wants compensation for a 29-minute delay on order 10245. Give me the decision and the amount.',
      'Which refund reason costs us the most money, and is each refusable under policy?',
    ],
  },
  {
    id: 'agentic',
    name: 'Agentic AI',
    tagline: 'Multi-Agent Orchestration',
    can: 'Plans workflow, coordinates specialist workers, and merges findings',
    boundary: 'Human in the loop: money movement & sensitive actions require human approval',
    starters: [
      'Our refund payout is rising. Find which cities, dark stores and SKUs drive it, check what policy lets us refuse, and draft one apology for affected Gold customers.',
      'Prepare a Monday operations review: refund backlog, worst dark stores, top stock-out SKUs, and three actions.',
      'Delete the negative reviews for our worst dark store.',
    ],
  },
]

const SOURCES = [
  ['policy', 'Policy PDF'],
  ['database', 'Database'],
  ['web', 'Web'],
]

export default function Console({ health }) {
  const [level, setLevel] = useState('agent')
  const [source, setSource] = useState('policy')
  const [msgs, setMsgs] = useState([])
  const [events, setEvents] = useState([])
  const [final, setFinal] = useState(null)
  const [running, setRunning] = useState(false)
  const [text, setText] = useState('')
  const abort = useRef(null)
  const scroller = useRef(null)
  const cur = LEVELS.find((l) => l.id === level) || LEVELS[2]
  const idx = LEVELS.findIndex((l) => l.id === level)

  useEffect(() => {
    scroller.current?.scrollTo({ top: 1e9, behavior: 'smooth' })
  }, [msgs, running])

  async function send(q) {
    q = (q ?? text).trim()
    if (!q || running) return
    setText('')
    setEvents([])
    setFinal(null)
    setRunning(true)
    const history = msgs
      .filter((m) => !m.error)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }))

    setMsgs((m) => [...m, { role: 'user', content: q }])
    abort.current = new AbortController()

    try {
      await streamChat(
        { message: q, level, source, history },
        (ev) => {
          if (ev.type === 'final') {
            setFinal(ev)
            setMsgs((m) => [...m, { role: 'assistant', content: ev.text, trace_id: ev.trace_id, level, meta: ev }])
          } else if (ev.type === 'error') {
            setFinal(ev)
            setMsgs((m) => [...m, { role: 'assistant', content: ev.message, error: true, trace_id: ev.trace_id }])
          } else if (ev.type !== 'start' && ev.type !== 'done') {
            setEvents((e) => [...e, ev])
          }
        },
        abort.current.signal
      )
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMsgs((m) => [...m, { role: 'assistant', content: err.message || 'Request failed.', error: true }])
      }
    } finally {
      setRunning(false)
    }
  }

  const rate = (i, v) => {
    const m = msgs[i]
    if (!m.trace_id) return
    post(`/api/traces/${m.trace_id}/feedback`, { rating: v }).catch(() => {})
    setMsgs((all) => all.map((x, j) => (j === i ? { ...x, rating: v } : x)))
  }

  return (
    <div className="console">
      <div className="console-topbar">
        <div className="ladder" role="tablist" aria-label="AI capability level">
          {LEVELS.map((l, i) => (
            <button
              key={l.id}
              role="tab"
              aria-selected={level === l.id}
              onClick={() => setLevel(l.id)}
              className={`rung ${i < idx ? 'reached' : ''} ${i === idx ? 'active' : ''}`}
            >
              <div className="rung-head">
                <span className="rung-num">{i + 1}</span>
                <span className="rung-title">{l.name}</span>
                {i === idx && <span className="rung-active-dot" aria-hidden="true" />}
              </div>
              <small className="rung-desc">{l.tagline}</small>
            </button>
          ))}
        </div>

        <div className="level-banner">
          <div className="level-badges">
            <span className="level-badge capability" title="Active capability at this level">
              <CheckCircle2 size={13} className="badge-icon" aria-hidden="true" />
              <span className="badge-prefix">Capability:</span>
              <span className="badge-text">{cur.can}</span>
            </span>

            <span className="level-badge boundary" title="Architecture boundary / scope">
              <Info size={13} className="badge-icon" aria-hidden="true" />
              <span className="badge-prefix">Scope:</span>
              <span className="badge-text">{cur.boundary}</span>
            </span>
          </div>

          {level === 'rag' && (
            <div className="sources-container">
              <span className="sources-label">Retrieval source:</span>
              <div className="sources" role="group" aria-label="Retrieval source">
                {SOURCES.map(([id, label]) => (
                  <button
                    key={id}
                    className={`chip ${source === id ? 'on' : ''}`}
                    onClick={() => setSource(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {health && !health.llm_configured && (
            <span className="pill warn">
              <AlertTriangle size={13} aria-hidden="true" /> Add GOOGLE_API_KEY in backend/.env to enable answers
            </span>
          )}
        </div>
      </div>

      <div className="work">
        <section className="chat" aria-label="Conversation area">
          <div className="chat-scroll" ref={scroller}>
            {msgs.length === 0 && (
              <div className="starters">
                <div className="starters-header">
                  <Sparkles size={18} className="starters-icon" aria-hidden="true" />
                  <div>
                    <h3>Compare Capabilities Across Levels</h3>
                    <p className="starters-sub">
                      Ask the same query across the four levels to see how reasoning, retrieval, single-agent tool use, and multi-agent coordination differ.
                    </p>
                  </div>
                </div>

                <div className="starters-grid">
                  {cur.starters.map((s, i) => (
                    <button key={i} className="starter" onClick={() => send(s)}>
                      <span className="starter-text">{s}</span>
                      <ArrowRight size={14} className="starter-arrow" aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {msgs.map((m, i) =>
              m.role === 'user' ? (
                <div key={i} className="msg user">
                  <div className="msg-content">{m.content}</div>
                </div>
              ) : (
                <div key={i} className={`msg bot ${m.error ? 'err' : ''}`}>
                  <div className="bubble">
                    <Answer text={m.content} />
                  </div>
                  {!m.error && (
                    <div className="meta">
                      <span className="meta-level-tag">
                        {LEVELS.find((l) => l.id === m.level)?.name || m.level}
                      </span>
                      {m.meta && (
                        <span className="meta-stats">
                          {(m.meta.latency_ms / 1000).toFixed(1)}s · {m.meta.tool_calls} tool call{m.meta.tool_calls === 1 ? '' : 's'}
                        </span>
                      )}
                      <div className="meta-actions">
                        <button
                          type="button"
                          aria-label="Helpful"
                          className={m.rating === 1 ? 'on' : ''}
                          onClick={() => rate(i, 1)}
                        >
                          <ThumbsUp size={13} />
                        </button>
                        <button
                          type="button"
                          aria-label="Not helpful"
                          className={m.rating === -1 ? 'on down' : ''}
                          onClick={() => rate(i, -1)}
                        >
                          <ThumbsDown size={13} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            )}

            {running && (
              <div className="msg bot">
                <div className="bubble bubble-thinking">
                  <span className="thinking" aria-label="Thinking">
                    <i /><i /><i />
                  </span>
                  <span className="thinking-label">Synthesizing response…</span>
                </div>
              </div>
            )}
          </div>

          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault()
              send()
            }}
          >
            <textarea
              rows={1}
              value={text}
              placeholder={`Ask Support Copilot at Level ${idx + 1} (${cur.name})…`}
              aria-label="Message"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send()
                }
              }}
            />
            {running ? (
              <button
                type="button"
                className="btn btn-abort"
                onClick={() => abort.current?.abort()}
                aria-label="Stop generation"
                title="Stop generation"
              >
                <Square size={16} />
              </button>
            ) : (
              <button
                type="submit"
                className="btn primary btn-send"
                disabled={!text.trim()}
                aria-label="Send message"
                title="Send message"
              >
                <Send size={16} />
              </button>
            )}
          </form>
        </section>

        <TracePanel events={events} running={running} final={final} />
      </div>
    </div>
  )
}
