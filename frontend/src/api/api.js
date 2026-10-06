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

export async function enableDemo() {
  const res = await apiFetch(`${API_BASE}/api/demo/enable`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json()).detail || 'enable failed')
  return res.json()
}

export async function disableDemo() {
  const res = await apiFetch(`${API_BASE}/api/demo/disable`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json()).detail || 'disable failed')
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

export async function startScenario(name = 'corporate_breach') {
  const res = await apiFetch(`${API_BASE}/api/scenario/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || 'start failed')
  return res.json()
}

export async function stopScenario() {
  const res = await apiFetch(`${API_BASE}/api/scenario/stop`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json()).detail || 'stop failed')
  return res.json()
}

export async function fetchScenarioStatus() {
  const res = await apiFetch(`${API_BASE}/api/scenario/status`)
  if (!res.ok) return { is_running: false, current_act: 0, act_name: '', progress: 0, narrative_text: '' }
  return res.json()
}

export async function resetDemo() {
  const res = await apiFetch(`${API_BASE}/api/admin/reset-demo`, {
    method: 'POST',
    headers: { 'X-Confirm-Reset': 'yes' },
  })
  if (!res.ok) throw new Error((await res.json()).detail || 'reset failed')
  return res.json()
}

export async function fetchTriageStats() {
  const res = await apiFetch(`${API_BASE}/api/triage/stats`)
  if (!res.ok) return { open_count: 0 }
  return res.json()
}

export async function fetchExplainSummary() {
  const res = await apiFetch(`${API_BASE}/api/explain/summary`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchGeoIP(ip) {
  const res = await apiFetch(`${API_BASE}/api/geo/${encodeURIComponent(ip)}`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchGeoSummary() {
  const res = await apiFetch(`${API_BASE}/api/geo/summary`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchGeoAttackers() {
  const res = await apiFetch(`${API_BASE}/api/geo/attackers`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchCampaigns(status = null, limit = 50) {
  const params = new URLSearchParams({ limit })
  if (status) params.set('status', status)
  const res = await apiFetch(`${API_BASE}/api/campaigns?${params}`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchActiveCampaigns() {
  const res = await apiFetch(`${API_BASE}/api/campaigns/active`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchCampaignStats() {
  const res = await apiFetch(`${API_BASE}/api/campaigns/stats`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchCampaign(id) {
  const res = await apiFetch(`${API_BASE}/api/campaigns/${encodeURIComponent(id)}`)
  if (!res.ok) return null
  return res.json()
}

export async function resolveCampaign(id) {
  const res = await apiFetch(`${API_BASE}/api/campaigns/${encodeURIComponent(id)}/resolve`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'resolve failed')
  return res.json()
}

// ── CVE (Phase 5C) ────────────────────────────────────────────────────────────
export async function fetchCVEStats() {
  const res = await apiFetch(`${API_BASE}/api/cve/stats`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchRecentCVEs(days = 7) {
  const res = await apiFetch(`${API_BASE}/api/cve/recent?days=${days}`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchCVEMatches(attackType) {
  const res = await apiFetch(`${API_BASE}/api/cve/match/${encodeURIComponent(attackType)}`)
  if (!res.ok) return []
  return res.json()
}

export async function refreshCVEFeed() {
  const res = await apiFetch(`${API_BASE}/api/cve/refresh`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'refresh failed')
  return res.json()
}

// ── Baseline (Phase 5D) ───────────────────────────────────────────────────────
export async function fetchBaselineStatus() {
  const res = await apiFetch(`${API_BASE}/api/baseline/status`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchBaselineChart() {
  const res = await apiFetch(`${API_BASE}/api/baseline/chart`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchBaselineHourStats(hour) {
  const res = await apiFetch(`${API_BASE}/api/baseline/stats/${hour}`)
  if (!res.ok) return null
  return res.json()
}

export async function fetchBaselineAlerts() {
  const res = await apiFetch(`${API_BASE}/api/baseline/alerts`)
  if (!res.ok) return []
  return res.json()
}

// ── Rules (Phase 6A) ──────────────────────────────────────────────────────────
export async function fetchRules() {
  const res = await apiFetch(`${API_BASE}/api/rules`)
  if (!res.ok) return []
  return res.json()
}

export async function createRule(data) {
  const res = await apiFetch(`${API_BASE}/api/rules`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'create failed')
  return res.json()
}

export async function updateRule(id, data) {
  const res = await apiFetch(`${API_BASE}/api/rules/${encodeURIComponent(id)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'update failed')
  return res.json()
}

export async function deleteRule(id) {
  const res = await apiFetch(`${API_BASE}/api/rules/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'delete failed')
  return res.json()
}

export async function toggleRule(id) {
  const res = await apiFetch(`${API_BASE}/api/rules/${encodeURIComponent(id)}/toggle`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'toggle failed')
  return res.json()
}

export async function evaluateRule(detection) {
  const res = await apiFetch(`${API_BASE}/api/rules/evaluate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(detection),
  })
  if (!res.ok) return null
  return res.json()
}

// ── Webhooks (Phase 6C) ───────────────────────────────────────────────────────
export async function fetchWebhooks() {
  const res = await apiFetch(`${API_BASE}/api/webhooks`)
  if (!res.ok) return []
  return res.json()
}

export async function createWebhook(data) {
  const res = await apiFetch(`${API_BASE}/api/webhooks`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'create failed')
  return res.json()
}

export async function updateWebhook(id, data) {
  const res = await apiFetch(`${API_BASE}/api/webhooks/${encodeURIComponent(id)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'update failed')
  return res.json()
}

export async function deleteWebhook(id) {
  const res = await apiFetch(`${API_BASE}/api/webhooks/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'delete failed')
  return res.json()
}

export async function testWebhook(id) {
  const res = await apiFetch(`${API_BASE}/api/webhooks/${encodeURIComponent(id)}/test`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'test failed')
  return res.json()
}

export async function toggleWebhook(id) {
  const res = await apiFetch(`${API_BASE}/api/webhooks/${encodeURIComponent(id)}/toggle`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'toggle failed')
  return res.json()
}

export async function fetchWebhookDeliveries(id) {
  const res = await apiFetch(`${API_BASE}/api/webhooks/${encodeURIComponent(id)}/deliveries`)
  if (!res.ok) return []
  return res.json()
}

// ── NLQ (Phase 6D) ────────────────────────────────────────────────────────────
export async function nlqQuery(query) {
  const res = await apiFetch(`${API_BASE}/api/nlq`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query }),
  })
  if (!res.ok) return { error: (await res.json().catch(() => ({}))).detail || 'query failed' }
  return res.json()
}

// ── Push (Phase 6E) ───────────────────────────────────────────────────────────
export async function fetchVapidPublicKey() {
  const res = await fetch(`${API_BASE}/api/push/vapid-public-key`)
  if (!res.ok) return null
  return res.json()
}

export async function subscribePush(subscription) {
  const res = await apiFetch(`${API_BASE}/api/push/subscribe`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(subscription),
  })
  if (!res.ok) return null
  return res.json()
}

export async function unsubscribePush(endpoint) {
  const res = await apiFetch(`${API_BASE}/api/push/subscribe`, {
    method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ endpoint }),
  })
  return res.ok
}

// ── Scheduled Replay (Phase 7) ─────────────────────────────────────────────────
export async function fetchScheduleStatus() {
  const res = await apiFetch(`${API_BASE}/api/schedule/status`)
  if (!res.ok) return null
  return res.json()
}

export async function setSchedule(cron) {
  const res = await apiFetch(`${API_BASE}/api/schedule/set`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ cron }),
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'set failed')
  return res.json()
}

export async function disableSchedule() {
  const res = await apiFetch(`${API_BASE}/api/schedule/disable`, { method: 'POST' })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'disable failed')
  return res.json()
}

export { API_BASE }
