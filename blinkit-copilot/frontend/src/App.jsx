import { lazy, Suspense, useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { MessagesSquare, LayoutDashboard, ShieldCheck, History, Activity, Database, Globe, Cpu } from 'lucide-react'
import { api } from './api'
import Console from './pages/Console.jsx'
const Operations = lazy(() => import('./pages/Operations.jsx'))
import Approvals from './pages/Approvals.jsx'
import Traces from './pages/Traces.jsx'

const NAV = [
  ['/', 'Console', MessagesSquare],
  ['/operations', 'Operations', LayoutDashboard],
  ['/approvals', 'Approvals', ShieldCheck],
  ['/traces', 'Run history', History],
]

export default function App() {
  const [health, setHealth] = useState(null)
  const [pending, setPending] = useState(0)

  useEffect(() => {
    api('/api/health').then(setHealth).catch(() => setHealth({ status: 'down' }))
    const tick = () => api('/api/approvals?status=PENDING').then((r) => setPending(r.length)).catch(() => {})
    tick()
    const id = setInterval(tick, 15000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="shell">
      <nav className="rail" aria-label="Main Navigation">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span className="brand-mark-inner" />
          </div>
          <div className="brand-info">
            <span className="brand-name">Support Copilot</span>
            <span className="brand-tag">Enterprise AI Console</span>
          </div>
        </div>

        <ul className="nav-list">
          {NAV.map(([to, label, Icon]) => (
            <li key={to}>
              <NavLink to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}>
                <Icon size={18} className="nav-icon" aria-hidden="true" />
                <span className="nav-label">{label}</span>
                {label === 'Approvals' && pending > 0 && <b className="badge">{pending}</b>}
              </NavLink>
            </li>
          ))}
        </ul>

        <HealthBox h={health} />
      </nav>

      <main className="main">
        <Routes>
          <Route path="/" element={<Console health={health} />} />
          <Route
            path="/operations"
            element={
              <Suspense fallback={<div className="page muted">Loading analytics…</div>}>
                <Operations />
              </Suspense>
            }
          />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/traces" element={<Traces />} />
        </Routes>
      </main>
    </div>
  )
}

function HealthBox({ h }) {
  if (!h) {
    return (
      <div className="health-card">
        <div className="health-header">
          <Activity size={14} className="health-icon" aria-hidden="true" />
          <span>System Status</span>
        </div>
        <p className="health-connecting">Connecting to backend…</p>
      </div>
    )
  }

  if (h.status !== 'ok') {
    return (
      <div className="health-card bad">
        <div className="health-header">
          <Activity size={14} className="health-icon" aria-hidden="true" />
          <span>System Status</span>
        </div>
        <div className="health-error">Backend unreachable</div>
      </div>
    )
  }

  return (
    <div className="health-card">
      <div className="health-header">
        <Activity size={13} className="health-icon" aria-hidden="true" />
        <span>System Status</span>
      </div>

      <div className="health-items">
        <div className="health-row" title={`Model: ${h.model}`}>
          <div className="health-label">
            <Cpu size={13} aria-hidden="true" />
            <span>LLM Model</span>
          </div>
          <span className="health-status">
            <i className={`dot ${h.llm_configured ? 'ok' : 'warn'}`} />
            <span className="health-val">{h.llm_configured ? h.model : 'No key'}</span>
          </span>
        </div>

        <div className="health-row" title={`Policy chunks: ${h.index?.chunks || 0} (${h.index?.mode || 'off'})`}>
          <div className="health-label">
            <Database size={13} aria-hidden="true" />
            <span>Policy Index</span>
          </div>
          <span className="health-status">
            <i className={`dot ${h.index?.chunks ? 'ok' : 'warn'}`} />
            <span className="health-val">{h.index?.chunks || 0} chunks</span>
          </span>
        </div>

        <div className="health-row" title={h.web_search_configured ? 'Web search enabled' : 'Web search disabled (TAVILY_API_KEY missing)'}>
          <div className="health-label">
            <Globe size={13} aria-hidden="true" />
            <span>Web Search</span>
          </div>
          <span className="health-status">
            <i className={`dot ${h.web_search_configured ? 'ok' : 'off'}`} />
            <span className="health-val">{h.web_search_configured ? 'Online' : 'Disabled'}</span>
          </span>
        </div>
      </div>
    </div>
  )
}
