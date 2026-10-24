const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const KEY = import.meta.env.VITE_API_KEY || ''

const headers = (extra = {}) => ({
  'Content-Type': 'application/json',
  ...(KEY ? { 'X-API-Key': KEY } : {}),
  ...extra,
})

export async function api(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, { ...opts, headers: headers(opts.headers) })
  if (!res.ok) {
    let msg = res.statusText
    try { msg = (await res.json()).detail || msg } catch { /* not json */ }
    throw new Error(msg)
  }
  return res.json()
}

export const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) })

/** POST + read a Server-Sent Events stream. Calls onEvent(obj) for every `data:` frame. */
export async function streamChat(body, onEvent, signal) {
  const res = await fetch(`${BASE}/api/chat`, { method: 'POST', headers: headers(), body: JSON.stringify(body), signal })
  if (!res.ok || !res.body) {
    let msg = res.statusText
    try { msg = (await res.json()).detail || msg } catch { /* not json */ }
    throw new Error(msg)
  }
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const frame = buf.slice(0, i)
      buf = buf.slice(i + 2)
      if (frame.startsWith('data:')) {
        try { onEvent(JSON.parse(frame.slice(5).trim())) } catch { /* ignore partial frame */ }
      }
    }
  }
}
