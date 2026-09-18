/**
 * Triage — Phase 3 / Task 1
 * Case management table for SOC analysts.
 * Monochrome base with explicit color exceptions for severity/status/SLA (carry meaning).
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { ClipboardList, X, CheckCheck, Clock, AlertTriangle } from 'lucide-react'
import { API_BASE } from '../api/api'
import { useDetectionStream } from '../hooks/useDetectionStream'
import './Triage.css'

const T = {
  bg:     '#000000',
  panel:  '#0a0a0a',
  border: 'rgba(255,255,255,0.10)',
  borderMid: 'rgba(255,255,255,0.18)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

const panelStyle = {
  background: `linear-gradient(${T.panel}, ${T.panel}) padding-box, linear-gradient(135deg, rgba(255,255,255,0.13) 0%, rgba(255,255,255,0.04) 100%) border-box`,
  border: '1px solid transparent',
  borderRadius: '18px',
  boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 2px 16px rgba(0,0,0,0.8)',
}

// ── Severity colors (explicit hue exception — carries triage meaning) ──────
const SEV = {
  critical: { bg: 'rgba(220,50,50,0.15)',  border: 'rgba(220,50,50,0.45)',  color: '#ff8080' },
  high:     { bg: 'rgba(255,140,0,0.14)',  border: 'rgba(255,140,0,0.45)',  color: '#ffb347' },
  medium:   { bg: 'rgba(255,204,51,0.12)', border: 'rgba(255,204,51,0.40)', color: '#ffe08a' },
  low:      { bg: 'rgba(255,255,255,0.05)',border: 'rgba(255,255,255,0.15)',color: 'rgba(255,255,255,0.55)' },
}

// ── Status colors ─────────────────────────────────────────────────────────
const STAT = {
  open:          { bg: 'rgba(255,255,255,0.12)', border: 'rgba(255,255,255,0.35)', color: '#fff' },
  acknowledged:  { bg: 'rgba(51,150,255,0.12)',  border: 'rgba(51,150,255,0.40)',  color: '#80bfff' },
  investigating: { bg: 'rgba(255,180,0,0.12)',   border: 'rgba(255,180,0,0.40)',   color: '#ffd080' },
  resolved:      { bg: 'rgba(50,200,100,0.12)',  border: 'rgba(50,200,100,0.40)',  color: '#80ff90' },
  false_positive:{ bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.45)' },
}

const SLA_COLOR = { ok: '#80ff90', warning: '#ffe08a', breached: '#ff8080' }
const SLA_ICON  = { ok: '✓', warning: '⚠', breached: '✗' }

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('apex_token')
  return fetch(url, {
    ...opts,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  })
}

function Badge({ map, value, style = {} }) {
  const c = map[value] || map.low || {}
  return (
    <span style={{
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
      padding: '3px 9px', borderRadius: '6px',
      fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 700,
      letterSpacing: '0.04em', textTransform: 'uppercase', ...style,
    }}>
      {value?.replace(/_/g, ' ')}
    </span>
  )
}

function StatCard({ label, value, sub }) {
  return (
    <div style={{ ...panelStyle, flex: '1 1 160px', padding: '18px 20px' }}>
      <div style={{ fontFamily: "'Inter',sans-serif", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: '26px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>{value ?? '—'}</div>
      {sub && <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, marginTop: '4px' }}>{sub}</div>}
    </div>
  )
}

// ── Edit/View panel ───────────────────────────────────────────────────────
function EditPanel({ caseItem, onClose, onSaved }) {
  const [status, setStatus]     = useState(caseItem.status)
  const [assignedTo, setAssignedTo] = useState(caseItem.assigned_to || '')
  const [notes, setNotes]       = useState(caseItem.notes || '')
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState(null)

  useEffect(() => {
    setStatus(caseItem.status)
    setAssignedTo(caseItem.assigned_to || '')
    setNotes(caseItem.notes || '')
  }, [caseItem.id])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await authFetch(`${API_BASE}/api/triage/${caseItem.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, assigned_to: assignedTo || null, notes: notes || null }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }
      const updated = await res.json()
      onSaved(updated)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const sev = SEV[caseItem.severity] || SEV.low

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: '400px',
      background: '#050505', borderLeft: '1px solid rgba(255,255,255,0.12)',
      zIndex: 1000, overflowY: 'auto', padding: '26px 24px',
      boxShadow: '-8px 0 40px rgba(0,0,0,0.7)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '22px' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '6px' }}>Triage Case</div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.text, fontWeight: 700, letterSpacing: '0.04em' }}>
            {caseItem.attack_type?.replace(/_/g, ' ').toUpperCase()}
          </div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted, marginTop: '3px' }}>
            {caseItem.source_ip}
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.dim, padding: '4px', lineHeight: 0 }}>
          <X size={16} />
        </button>
      </div>

      {/* Meta grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '20px' }}>
        {[
          ['ID', caseItem.id?.slice(0, 8) + '…'],
          ['Severity', <Badge map={SEV} value={caseItem.severity} />],
          ['Created', caseItem.created_at ? new Date(caseItem.created_at).toLocaleString() : '—'],
          ['SLA', (() => {
            const col = SLA_COLOR[caseItem.sla_status] || T.muted
            return (
              <span style={{ color: col, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 700 }}>
                {SLA_ICON[caseItem.sla_status] || '?'} {caseItem.sla_status?.toUpperCase()}
              </span>
            )
          })()],
        ].map(([k, v]) => (
          <div key={k} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: '10px', padding: '10px 12px' }}>
            <div style={{ fontFamily: "'Inter',sans-serif", fontSize: '9px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>{k}</div>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.text }}>{v}</div>
          </div>
        ))}
      </div>

      {/* Status */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ fontFamily: "'Inter',sans-serif", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '7px' }}>Status</div>
        <select
          value={status}
          onChange={e => setStatus(e.target.value)}
          style={{ width: '100%', background: '#111', border: '1px solid rgba(255,255,255,0.18)', borderRadius: '8px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', padding: '9px 12px', outline: 'none' }}
        >
          {['open', 'acknowledged', 'investigating', 'resolved', 'false_positive'].map(s => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {/* Assigned to */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ fontFamily: "'Inter',sans-serif", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '7px' }}>Assigned To</div>
        <input
          value={assignedTo}
          onChange={e => setAssignedTo(e.target.value)}
          placeholder="analyst username"
          style={{ width: '100%', boxSizing: 'border-box', background: '#111', border: '1px solid rgba(255,255,255,0.18)', borderRadius: '8px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', padding: '9px 12px', outline: 'none' }}
        />
      </div>

      {/* Notes */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontFamily: "'Inter',sans-serif", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '7px' }}>Analyst Notes</div>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          rows={5}
          placeholder="Investigation notes…"
          style={{ width: '100%', boxSizing: 'border-box', background: '#111', border: '1px solid rgba(255,255,255,0.18)', borderRadius: '8px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', padding: '10px 12px', resize: 'vertical', outline: 'none', lineHeight: '1.6' }}
        />
      </div>

      {error && (
        <div style={{ marginBottom: '12px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: '#ff8080' }}>{error}</div>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        style={{ width: '100%', padding: '11px 0', background: saving ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.10)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: '10px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', fontWeight: 700, cursor: saving ? 'default' : 'pointer', transition: 'background 0.15s' }}
      >
        {saving ? 'Saving…' : 'Save Changes'}
      </button>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────
function Triage() {
  const [cases, setCases]         = useState([])
  const [stats, setStats]         = useState(null)
  const [filterStatus, setFilterStatus]   = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [filterMe, setFilterMe]   = useState(false)
  const [editCase, setEditCase]   = useState(null)
  const [newIds, setNewIds]       = useState(new Set())
  const [loading, setLoading]     = useState(true)
  const prevIdsRef  = useRef(new Set())
  const wsTriggered = useRef(false)

  const buildUrl = useCallback(() => {
    const params = new URLSearchParams()
    if (filterStatus)   params.set('status', filterStatus)
    if (filterSeverity) params.set('severity', filterSeverity)
    if (filterMe)       params.set('assigned_to', 'me')
    return `${API_BASE}/api/triage?${params}`
  }, [filterStatus, filterSeverity, filterMe])

  const loadCases = useCallback(async (fromWs = false) => {
    try {
      const res = await authFetch(buildUrl())
      if (!res.ok) return
      const data = await res.json()
      const currentIds = new Set(data.map(c => c.id))
      if (fromWs && prevIdsRef.current.size > 0) {
        const added = data.filter(c => !prevIdsRef.current.has(c.id)).map(c => c.id)
        if (added.length > 0) {
          setNewIds(new Set(added))
          setTimeout(() => setNewIds(new Set()), 3000)
        }
      }
      prevIdsRef.current = currentIds
      setCases(data)
    } catch { }
    setLoading(false)
  }, [buildUrl])

  const loadStats = useCallback(async () => {
    try {
      const res = await authFetch(`${API_BASE}/api/triage/stats`)
      if (res.ok) setStats(await res.json())
    } catch { }
  }, [])

  useEffect(() => {
    loadCases()
    loadStats()
    const iv = setInterval(() => { loadCases(); loadStats() }, 10000)
    return () => clearInterval(iv)
  }, [loadCases, loadStats])

  // Re-fetch when filters change
  useEffect(() => { loadCases() }, [loadCases])

  const onDetection = useCallback((d) => {
    if (d.label && d.label !== 'normal') {
      wsTriggered.current = true
      setTimeout(() => loadCases(true), 1200)
      loadStats()
    }
  }, [loadCases, loadStats])
  useDetectionStream(onDetection)

  const handleAcknowledge = async (caseId, e) => {
    e.stopPropagation()
    try {
      const res = await authFetch(`${API_BASE}/api/triage/${caseId}/acknowledge`, { method: 'POST' })
      if (res.ok) {
        const updated = await res.json()
        setCases(prev => prev.map(c => c.id === updated.id ? updated : c))
        if (editCase?.id === updated.id) setEditCase(updated)
      }
    } catch { }
  }

  const handleSaved = (updated) => {
    setCases(prev => prev.map(c => c.id === updated.id ? updated : c))
    setEditCase(updated)
    loadStats()
  }

  const fmtMins = (m) => {
    if (m == null) return '—'
    if (m < 60)   return `${Math.round(m)}m`
    return `${(m / 60).toFixed(1)}h`
  }

  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>
          Security Operations
        </div>
        <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: '22px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
          Alert Triage
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
        <StatCard label="Open Cases"        value={stats?.open_count ?? '—'} />
        <StatCard label="SLA Breached"      value={stats?.sla_breach_count ?? '—'} sub={stats ? `${(stats.sla_breach_rate * 100).toFixed(0)}% breach rate` : undefined} />
        <StatCard label="Avg Resolution"    value={fmtMins(stats?.avg_resolution_minutes)} sub="last 7 days" />
        <StatCard label="False Positive %" value={stats ? `${(stats.false_positive_rate * 100).toFixed(1)}%` : '—'} sub="last 7 days" />
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '16px', alignItems: 'center' }}>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          style={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.18)', borderRadius: '8px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', padding: '8px 12px', outline: 'none' }}
        >
          <option value="">All Statuses</option>
          {['open','acknowledged','investigating','resolved','false_positive'].map(s => (
            <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={e => setFilterSeverity(e.target.value)}
          style={{ background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.18)', borderRadius: '8px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', padding: '8px 12px', outline: 'none' }}
        >
          <option value="">All Severities</option>
          {['critical','high','medium','low'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={filterMe}
            onChange={e => setFilterMe(e.target.checked)}
            style={{ accentColor: '#fff' }}
          />
          Assigned to me
        </label>
        <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>
          {cases.length} case{cases.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="table-container">
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ClipboardList size={12} style={{ color: T.muted }} />
            <span className="chart-title" style={{ margin: 0 }}>Cases</span>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.dim }}>
            loading…
          </div>
        ) : cases.length === 0 ? (
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.dim }}>
            no triage cases
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>IP</th>
                <th>Attack Type</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Assigned To</th>
                <th>SLA</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {cases.map(c => {
                const isNew = newIds.has(c.id)
                return (
                  <tr
                    key={c.id}
                    className={isNew ? 'triage-row-new' : ''}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setEditCase(c)}
                  >
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>
                      {c.id?.slice(0, 8)}…
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', fontWeight: 600, color: T.text }}>
                      {c.source_ip}
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted }}>
                      {c.attack_type?.replace(/_/g, ' ')}
                    </td>
                    <td><Badge map={SEV} value={c.severity} /></td>
                    <td><Badge map={STAT} value={c.status} /></td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted }}>
                      {c.assigned_to || <span style={{ color: T.dim }}>—</span>}
                    </td>
                    <td>
                      <span style={{ color: SLA_COLOR[c.sla_status] || T.dim, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', fontWeight: 700 }}>
                        {SLA_ICON[c.sla_status] || '?'}
                      </span>
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>
                      {c.created_at ? new Date(c.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {c.status === 'open' && (
                          <button
                            onClick={e => handleAcknowledge(c.id, e)}
                            className="time-btn"
                            style={{ padding: '4px 10px', fontSize: '9px', display: 'flex', alignItems: 'center', gap: '4px', textTransform: 'none', letterSpacing: '0.02em' }}
                          >
                            <CheckCheck size={10} /> Ack
                          </button>
                        )}
                        <button
                          onClick={e => { e.stopPropagation(); setEditCase(c) }}
                          className="time-btn"
                          style={{ padding: '4px 10px', fontSize: '9px', textTransform: 'none', letterSpacing: '0.02em' }}
                        >
                          View
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Slide-in panel */}
      {editCase && (
        <>
          <div onClick={() => setEditCase(null)} style={{ position: 'fixed', inset: 0, zIndex: 999, background: 'rgba(0,0,0,0.3)' }} />
          <EditPanel
            caseItem={editCase}
            onClose={() => setEditCase(null)}
            onSaved={handleSaved}
          />
        </>
      )}
    </div>
  )
}

export default Triage
