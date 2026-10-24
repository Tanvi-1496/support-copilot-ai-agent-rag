import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  CreditCard,
  AlertTriangle,
  AlertOctagon,
  ArrowLeft,
  Inbox,
  Check,
  X,
  FileText,
  RotateCw,
  Info,
} from 'lucide-react'
import { api, post } from '../api'

const ACTION_CONFIG = {
  WALLET_CREDIT: {
    label: 'Wallet Credit',
    Icon: CreditCard,
    accentClass: 'action-credit',
  },
  ESCALATE_TICKET: {
    label: 'Escalate Ticket',
    Icon: AlertTriangle,
    accentClass: 'action-escalate',
  },
  STORE_WARNING: {
    label: 'Store Warning',
    Icon: AlertOctagon,
    accentClass: 'action-warning',
  },
}

const formatDate = (ts) => {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Approvals() {
  const [rows, setRows] = useState(null)
  const [tab, setTab] = useState('PENDING')
  const [notes, setNotes] = useState({})
  const [confirming, setConfirming] = useState(null) // { id, decision }
  const [submittingId, setSubmittingId] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    setErr('')
    try {
      const data = await api('/api/approvals')
      setRows(data || [])
    } catch (e) {
      setErr(e.message || 'Failed to load approvals queue.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const pendingCount = (rows || []).filter((r) => r.status === 'PENDING').length
  const approvedCount = (rows || []).filter((r) => r.status === 'APPROVED').length
  const rejectedCount = (rows || []).filter((r) => r.status === 'REJECTED').length
  const totalCount = (rows || []).length

  const filteredRows = (rows || []).filter((r) => {
    if (tab === 'ALL') return true
    return r.status === tab
  })

  async function handleDecision(id, decision) {
    setSubmittingId(id)
    setFeedback(null)
    setErr('')
    try {
      const note = (notes[id] || '').trim()
      const res = await post(`/api/approvals/${id}/decision`, { decision, note })
      setFeedback({
        type: 'success',
        message: `Proposal #${id} for Order #${res?.order_id || ''} was ${decision.toLowerCase()} and logged in the operational audit trail.`,
      })
      setConfirming(null)
      await loadData()
    } catch (e) {
      setFeedback({
        type: 'error',
        message: e.message || `Failed to record decision for proposal #${id}.`,
      })
    } finally {
      setSubmittingId(null)
    }
  }

  return (
    <div className="page approvals-page">
      {/* Page Header */}
      <div className="page-head">
        <div>
          <h1>Approval Center</h1>
          <p>Review AI-proposed actions before they are executed.</p>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={loadData}
          disabled={loading}
          title="Refresh queue"
        >
          <RotateCw size={14} className={loading ? 'spinning' : ''} aria-hidden="true" />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Governance & Human-in-the-Loop Notice */}
      <div className="approvals-governance-card">
        <div className="governance-icon-wrap">
          <ShieldCheck size={20} className="governance-icon" aria-hidden="true" />
        </div>
        <div className="governance-content">
          <span className="governance-title">Human-in-the-Loop Safety Governance</span>
          <p className="governance-text">
            AI agents operate under strict read-only constraints and cannot transfer funds or alter records autonomously.
            Reviewing a proposal verifies policy compliance and logs authorization in the operational audit trail.
            Financial transfers and ticketing dispatches require final operational execution.
          </p>
        </div>
      </div>

      {/* Compact Summary Metrics Row */}
      <div className="approvals-summary-row" role="region" aria-label="Approval statistics">
        <button
          type="button"
          className={`summary-metric-card ${tab === 'PENDING' ? 'active-metric' : ''} ${
            pendingCount > 0 ? 'has-pending' : ''
          }`}
          onClick={() => setTab('PENDING')}
        >
          <div className="metric-top">
            <span className="metric-label">Pending Review</span>
            <Clock size={16} className="metric-icon warn" aria-hidden="true" />
          </div>
          <div className="metric-val">{pendingCount}</div>
          <div className="metric-sub">Awaiting human authorization</div>
        </button>

        <button
          type="button"
          className={`summary-metric-card ${tab === 'APPROVED' ? 'active-metric' : ''}`}
          onClick={() => setTab('APPROVED')}
        >
          <div className="metric-top">
            <span className="metric-label">Approved</span>
            <CheckCircle2 size={16} className="metric-icon success" aria-hidden="true" />
          </div>
          <div className="metric-val">{approvedCount}</div>
          <div className="metric-sub">Authorized in audit log</div>
        </button>

        <button
          type="button"
          className={`summary-metric-card ${tab === 'REJECTED' ? 'active-metric' : ''}`}
          onClick={() => setTab('REJECTED')}
        >
          <div className="metric-top">
            <span className="metric-label">Rejected</span>
            <XCircle size={16} className="metric-icon error" aria-hidden="true" />
          </div>
          <div className="metric-val">{rejectedCount}</div>
          <div className="metric-sub">Declined by reviewer</div>
        </button>

        <button
          type="button"
          className={`summary-metric-card ${tab === 'ALL' ? 'active-metric' : ''}`}
          onClick={() => setTab('ALL')}
        >
          <div className="metric-top">
            <span className="metric-label">All Proposals</span>
            <FileText size={16} className="metric-icon info" aria-hidden="true" />
          </div>
          <div className="metric-val">{totalCount}</div>
          <div className="metric-sub">Total lifetime queue</div>
        </button>
      </div>

      {/* Filter Tabs Bar */}
      <div className="approvals-filter-bar">
        <div className="tabs" role="tablist" aria-label="Filter proposals by status">
          {[
            { id: 'PENDING', label: 'Pending', count: pendingCount },
            { id: 'APPROVED', label: 'Approved', count: approvedCount },
            { id: 'REJECTED', label: 'Rejected', count: rejectedCount },
            { id: 'ALL', label: 'All', count: totalCount },
          ].map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={tab === t.id}
              className={`chip ${tab === t.id ? 'on' : ''}`}
              onClick={() => {
                setTab(t.id)
                setConfirming(null)
              }}
            >
              <span>{t.label}</span>
              <span className="tab-count-badge">{t.count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Feedback Messages (Success / Error) */}
      {feedback && (
        <div className={`feedback-alert ${feedback.type === 'error' ? 'bad' : 'ok'}`}>
          <div className="feedback-content">
            {feedback.type === 'error' ? (
              <XCircle size={18} aria-hidden="true" />
            ) : (
              <CheckCircle2 size={18} aria-hidden="true" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            type="button"
            className="feedback-dismiss"
            onClick={() => setFeedback(null)}
            aria-label="Dismiss notification"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {err && (
        <div className="error-box">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>{err}</span>
        </div>
      )}

      {/* Content Area */}
      {loading && rows === null ? (
        <div className="approvals-loading-state">
          <span className="thinking"><i /><i /><i /></span>
          <p className="muted">Retrieving approval records…</p>
        </div>
      ) : filteredRows.length === 0 ? (
        /* Empty States */
        tab === 'PENDING' && pendingCount === 0 ? (
          <div className="card approvals-empty-state">
            <div className="empty-icon-circle ok">
              <CheckCircle2 size={36} aria-hidden="true" />
            </div>
            <h2 className="empty-title">All caught up</h2>
            <p className="empty-description">
              There are no proposed actions waiting for your review. When customer support or operations agents
              recommend refunds, customer goodwill credits, or store warnings, they will appear here.
            </p>
            <div className="empty-actions">
              <Link to="/" className="btn primary">
                <ArrowLeft size={16} aria-hidden="true" />
                <span>Return to Console</span>
              </Link>
            </div>
            <div className="empty-tip-box">
              <div className="tip-header">
                <Info size={14} aria-hidden="true" />
                <span>How to test approval requests:</span>
              </div>
              <p className="tip-text">
                In the Console, switch to Level 3 (AI Agent) or Level 4 (Agentic AI) and ask:
                <br />
                <em>"A Gold member wants compensation for a 29-minute delay on order 10245. Give me the decision and the amount."</em>
                <br />
                The agent will inspect policy (p.4) and submit an automated ₹150 wallet credit proposal for human review.
              </p>
            </div>
          </div>
        ) : (
          <div className="card approvals-empty-state">
            <div className="empty-icon-circle neutral">
              <Inbox size={36} aria-hidden="true" />
            </div>
            <h2 className="empty-title">No {tab.toLowerCase()} proposals</h2>
            <p className="empty-description">
              There are currently no proposals matching the "{tab.toLowerCase()}" filter in the audit queue.
            </p>
            <div className="empty-actions">
              <button type="button" className="btn" onClick={() => setTab('ALL')}>
                View All Proposals
              </button>
            </div>
          </div>
        )
      ) : (
        /* Proposal Cards List */
        <div className="approvals-list">
          {filteredRows.map((r) => {
            const conf = ACTION_CONFIG[r.action] || {
              label: r.action ? r.action.replace(/_/g, ' ') : 'Action',
              Icon: AlertTriangle,
              accentClass: 'action-default',
            }
            const ActionIcon = conf.Icon
            const isSubmitting = submittingId === r.id
            const isConfirming = confirming && confirming.id === r.id

            return (
              <div
                key={r.id}
                className={`card approval-card-pro ${r.status.toLowerCase()} ${
                  isConfirming ? 'confirm-active' : ''
                }`}
              >
                {/* Card Top: Badges & Status */}
                <div className="card-pro-head">
                  <div className="card-pro-badges">
                    <span className={`badge-action ${conf.accentClass}`}>
                      <ActionIcon size={14} aria-hidden="true" />
                      <span>{conf.label}</span>
                    </span>

                    <span className="badge-order">
                      Order #{r.order_id}
                    </span>

                    {r.amount > 0 && (
                      <span className="badge-amount">
                        ₹{Number(r.amount).toLocaleString('en-IN')}
                      </span>
                    )}

                    <span className="badge-id mono">
                      #{r.id}
                    </span>
                  </div>

                  <div className="card-pro-status">
                    {r.status === 'PENDING' && (
                      <span className="pill warn pill-status">
                        <i className="dot warn" /> Pending Review
                      </span>
                    )}
                    {r.status === 'APPROVED' && (
                      <span className="pill ok pill-status">
                        <Check size={13} aria-hidden="true" /> Approved
                      </span>
                    )}
                    {r.status === 'REJECTED' && (
                      <span className="pill bad pill-status">
                        <X size={13} aria-hidden="true" /> Rejected
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Body: Justification & Details */}
                <div className="card-pro-body">
                  <div className="reason-section">
                    <span className="reason-label">Agent Justification & Policy Reference:</span>
                    <p className="reason-text">{r.reason || 'No justification provided.'}</p>
                  </div>

                  {/* Metadata & Audit Information */}
                  <div className="card-pro-meta">
                    <span className="meta-timestamp">
                      <Clock size={13} aria-hidden="true" />
                      <span>Proposed {formatDate(r.ts)}</span>
                    </span>

                    {r.trace_id && (
                      <span className="meta-trace mono">
                        Trace #{r.trace_id}
                      </span>
                    )}
                  </div>

                  {/* Audit Decisions (if decided) */}
                  {r.status !== 'PENDING' && (
                    <div className="card-pro-audit">
                      <div className="audit-row">
                        <span className="audit-label">
                          {r.status === 'APPROVED' ? 'Decision Recorded:' : 'Rejection Recorded:'}
                        </span>
                        <span className="audit-time">{formatDate(r.decided_ts)}</span>
                      </div>
                      {r.decision_note && (
                        <div className="audit-note">
                          <span className="audit-note-label">Reviewer Note:</span>
                          <span className="audit-note-text">"{r.decision_note}"</span>
                        </div>
                      )}
                      <div className="audit-footer-note">
                        <Info size={12} aria-hidden="true" />
                        <span>Managerial authorization logged in audit trail. Downstream execution requires manual settlement.</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Action Panel for PENDING Proposals */}
                {r.status === 'PENDING' && (
                  <div className="card-pro-action-panel">
                    {isConfirming ? (
                      /* Inline Confirmation State */
                      <div className="confirm-box">
                        <div className="confirm-msg">
                          <AlertTriangle size={16} className="confirm-icon" aria-hidden="true" />
                          <span>
                            Confirm <b>{confirming.decision.toLowerCase()}</b> for Order #{r.order_id}
                            {r.amount > 0 && <> (₹{r.amount})</>}?
                          </span>
                        </div>
                        <div className="confirm-buttons">
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            disabled={isSubmitting}
                            onClick={() => setConfirming(null)}
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            className={`btn btn-sm ${
                              confirming.decision === 'APPROVED' ? 'primary' : 'danger'
                            }`}
                            disabled={isSubmitting}
                            onClick={() => handleDecision(r.id, confirming.decision)}
                          >
                            {isSubmitting ? (
                              <span>Processing…</span>
                            ) : confirming.decision === 'APPROVED' ? (
                              <span>Yes, Authorize Action</span>
                            ) : (
                              <span>Yes, Reject Proposal</span>
                            )}
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Standard Action Inputs */
                      <div className="action-row">
                        <input
                          type="text"
                          className="decision-note-input"
                          placeholder="Add optional reviewer decision note…"
                          aria-label={`Reviewer note for proposal #${r.id}`}
                          value={notes[r.id] || ''}
                          disabled={isSubmitting}
                          onChange={(e) =>
                            setNotes({ ...notes, [r.id]: e.target.value })
                          }
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault()
                              setConfirming({ id: r.id, decision: 'APPROVED' })
                            }
                          }}
                        />

                        <div className="action-buttons">
                          <button
                            type="button"
                            className="btn danger"
                            disabled={isSubmitting}
                            onClick={() => setConfirming({ id: r.id, decision: 'REJECTED' })}
                          >
                            <X size={15} aria-hidden="true" />
                            <span>Reject</span>
                          </button>
                          <button
                            type="button"
                            className="btn primary"
                            disabled={isSubmitting}
                            onClick={() => setConfirming({ id: r.id, decision: 'APPROVED' })}
                          >
                            <Check size={15} aria-hidden="true" />
                            <span>Authorize</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
