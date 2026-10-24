import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'

const fmt = (n) => (n == null ? '—' : Number(n).toLocaleString('en-IN'))
const AXIS = { fontSize: 12, fill: '#B2C2B7' }

function HBar({ data, x, y, color = '#16A34A', unit = '' }) {
  return (
    <div className="chart">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
          <CartesianGrid horizontal={false} stroke="#34463A" strokeOpacity={0.7} />
          <XAxis type="number" tick={AXIS} unit={unit} stroke="#34463A" />
          <YAxis type="category" dataKey={y} tick={AXIS} width={120} stroke="#34463A" />
          <Tooltip
            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
            contentStyle={{ backgroundColor: '#1B2922', borderColor: '#34463A', color: '#F4F7F4', borderRadius: '8px' }}
            formatter={(v) => [`${fmt(v)}${unit}`, 'Value']}
          />
          <Bar dataKey={x} radius={[0, 4, 4, 0]}>
            {data.map((_, i) => <Cell key={i} fill={i === 0 ? '#F87171' : color} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Operations() {
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => { api('/api/analytics/overview').then(setD).catch((e) => setErr(e.message)) }, [])

  if (err) return <div className="page"><div className="error-box">Could not load analytics: {err}</div></div>
  if (!d) return <div className="page"><p className="muted">Loading…</p></div>
  const k = d.kpis
  const gold = d.tier_compare?.find((t) => t.tier === 'GOLD')
  const reg = d.tier_compare?.find((t) => t.tier === 'REGULAR')

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Operations</h1>
          <p>The numbers the agents query, in one place. Ask the same questions in the Console and the answers should match these.</p>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi"><span>Orders</span><b>{fmt(k.orders)}</b><small>{fmt(k.delivered)} delivered</small></div>
        <div className="kpi"><span>Late deliveries</span><b>{k.late_pct ?? '—'}%</b><small>of delivered orders</small></div>
        <div className="kpi"><span>Refund payout</span><b>₹{fmt(k.refund_total)}</b><small>excluding rejected</small></div>
        <div className="kpi warn"><span>Stuck in processing</span><b>₹{fmt(k.pending_amount)}</b><small>{fmt(k.pending_count)} refunds</small></div>
        <div className="kpi"><span>Average CSAT</span><b>{k.avg_csat ?? '—'}</b><small>{fmt(k.open_tickets)} tickets not resolved</small></div>
      </div>

      <div className="grid2">
        <div className="card"><h3>Late rate by city</h3><p className="sub">Worst ten, cities with at least 30 deliveries</p>
          <HBar data={d.late_by_city} x="late_pct" y="city" unit="%" /></div>
        <div className="card"><h3>Refund cost by reason</h3><p className="sub">Rupees paid or processing</p>
          <HBar data={d.refunds_by_reason} x="amount" y="reason" color="#2c5fa8" /></div>
        <div className="card"><h3>What goes missing most</h3><p className="sub">Item-level MISSING count by product</p>
          <HBar data={d.missing_items} x="n" y="product" color="#7a4fb0" /></div>
        <div className="card"><h3>Do Gold members get a faster order?</h3><p className="sub">Delivered orders by membership tier</p>
          <div className="scroll-x"><table className="t"><thead><tr><th>Tier</th><th>Orders</th><th>Avg minutes</th><th>Late</th></tr></thead>
            <tbody>{d.tier_compare.map((t) => <tr key={t.tier}><td>{t.tier}</td><td>{fmt(t.delivered)}</td><td>{t.avg_minutes}</td><td>{t.late_pct}%</td></tr>)}</tbody></table></div>
          {gold && reg && <p className="muted" style={{ marginBottom: 0 }}>Gold is {Math.abs(gold.late_pct - reg.late_pct).toFixed(1)} points {gold.late_pct <= reg.late_pct ? 'better' : 'worse'} on lateness.</p>}
        </div>
        <div className="card" style={{ gridColumn: '1 / -1' }}><h3>Dark stores with the most refunds per 100 orders</h3><p className="sub">Stores with at least 30 orders</p>
          <div className="scroll-x"><table className="t"><thead><tr><th>Dark store</th><th>City</th><th>Orders</th><th>Refunds</th><th>Per 100 orders</th></tr></thead>
            <tbody>{d.worst_stores.map((s) => <tr key={s.dark_store}><td>{s.dark_store}</td><td>{s.city}</td><td>{fmt(s.orders)}</td><td>{fmt(s.refunds)}</td><td><b>{s.refunds_per_100_orders}</b></td></tr>)}</tbody></table></div>
        </div>
      </div>
    </div>
  )
}
