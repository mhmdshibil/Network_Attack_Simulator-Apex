const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000"

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`)
  return res.json()
}

export async function fetchTimeline(window = '1h') {
  const res = await fetch(`${API_BASE}/api/analytics/timeline?window=${window}`)
  return res.json()
}

export async function fetchTopAttackers() {
  const res = await fetch(`${API_BASE}/api/analytics/top_attackers`)
  return res.json()
}

export async function fetchAttackTrends() {
  const res = await fetch(`${API_BASE}/api/analytics/attack_trends`)
  return res.json()
}

export async function fetchRisk(window = '1h') {
  const res = await fetch(`${API_BASE}/api/analytics/risk?window=${window}`)
  return res.json()
}

export async function fetchDetections() {
  const res = await fetch(`${API_BASE}/api/detections`)
  return res.json()
}

export async function fetchBlockedIPs() {
  const res = await fetch(`${API_BASE}/api/system/blocked_ips`)
  return res.json()
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/metrics`)
  return res.json()
}

export async function fetchAlerts(limit = 20) {
  const res = await fetch(`${API_BASE}/api/alerts?limit=${limit}`)
  return res.json()
}
