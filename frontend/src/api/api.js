const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"

let _onUnauthorized = null

export function setUnauthorizedHandler(fn) {
  _onUnauthorized = fn
}

function authHeaders() {
  const token = localStorage.getItem('apex_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function apiFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...(options.headers || {}) },
  })
  if (res.status === 401 && _onUnauthorized) _onUnauthorized()
  return res
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  return res.json()
}

export async function fetchTimeline(window = '1h') {
  const res = await apiFetch(`${API_BASE}/api/analytics/timeline?window=${window}`)
  return res.json()
}

export async function fetchTopAttackers() {
  const res = await apiFetch(`${API_BASE}/api/analytics/top_attackers`)
  return res.json()
}

export async function fetchAttackTrends() {
  const res = await apiFetch(`${API_BASE}/api/analytics/attack_trends`)
  return res.json()
}

export async function fetchRisk(window = '1h') {
  const res = await apiFetch(`${API_BASE}/api/analytics/risk?window=${window}`)
  return res.json()
}

export async function fetchDetections() {
  const res = await apiFetch(`${API_BASE}/api/detections`)
  return res.json()
}

export async function fetchBlockedIPs() {
  const res = await apiFetch(`${API_BASE}/api/system/blocked_ips`)
  return res.json()
}

export async function fetchMetrics() {
  const res = await apiFetch(`${API_BASE}/api/metrics`)
  return res.json()
}

export async function fetchAlerts(limit = 20) {
  const res = await apiFetch(`${API_BASE}/api/alerts?limit=${limit}`)
  return res.json()
}

export async function fetchExplanation(ip, ts = null) {
  const params = new URLSearchParams({ ip })
  if (ts) params.set('ts', ts)
  const res = await apiFetch(`${API_BASE}/api/explain?${params}`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchSystemOverview() {
  const res = await apiFetch(`${API_BASE}/api/system/overview`)
  return res.json()
}

export async function fetchSystemMetrics() {
  const res = await apiFetch(`${API_BASE}/api/system/metrics`)
  return res.json()
}

export async function generateIncidentSummary(detection) {
  const res = await apiFetch(`${API_BASE}/api/incidents/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ip:         detection.ip,
      timestamp:  detection.timestamp,
      label:      detection.label,
      confidence: detection.confidence ?? 0,
      risk_score: detection.risk_score ?? 0,
      action:     detection.action ?? 'monitored',
    }),
  })
  if (!res.ok) return null
  return res.json()
}

export async function triggerDemoAttack(attackType = null) {
  const params = attackType ? `?type=${encodeURIComponent(attackType)}` : ''
  const res = await apiFetch(`${API_BASE}/api/demo/trigger${params}`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json()).detail || 'trigger failed')
  return res.json()
}

export async function fetchDemoStatus() {
  const res = await apiFetch(`${API_BASE}/api/demo/status`)
  return res.json()
}

export { API_BASE }
