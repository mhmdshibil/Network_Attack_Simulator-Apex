/**
 * DetectedAttacks — Phase 1 + 5 + 8
 *
 * - Streams events via WebSocket (falls back to polling on disconnect)
 * - Click any row to open a SHAP "why did this fire?" drawer
 */
import React, { useCallback, useState, useRef } from 'react'
import { AlertCircle, AlertTriangle, X, Zap } from 'lucide-react'
import { fetchDetections, fetchExplanation } from '../api/api'
import { useDetectionStream } from '../hooks/useDetectionStream'

const T = {
  bg:      '#131316',
  border:  '#232328',
  text:    '#F2F3F5',
  muted:   '#6E7180',
  accent:  '#2DD9FF',
  danger:  '#FF3B5C',
  warning: '#FFA63D',
  purple:  '#9B59B6',
}

const LABEL_COLORS = {
  ddos:             '#FF3B5C',
  port_scan:        '#FFA63D',
  sql_injection:    '#FF6D3B',
  bruteforce:       '#9B59B6',
  malware:          '#FF3B5C',
  unknown_anomaly:  '#2DD9FF',
}

const ACTION_STYLE = {
  blocked:      { color: '#FF3B5C', bg: 'rgba(255,59,92,0.1)',   border: 'rgba(255,59,92,0.25)',   label: 'BLOCK' },
  rate_limited: { color: '#FFA63D', bg: 'rgba(255,166,61,0.1)',  border: 'rgba(255,166,61,0.25)',  label: 'RATE-LIMIT' },
  monitored:    { color: '#2DD9FF', bg: 'rgba(45,217,255,0.08)', border: 'rgba(45,217,255,0.2)',   label: 'MONITOR' },
}

const MAX_ROWS = 200

// ── SHAP bar chart ────────────────────────────────────────────────────────────
function ShapBar({ feature, value, shap, direction }) {
  const pct = Math.min(Math.abs(shap) * 800, 100)
  const color = shap > 0 ? T.danger : T.accent
  return (
    <div style={{ marginBottom: '12px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text }}>
          {direction} {feature.replace(/_/g, ' ')}
        </span>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>
          val={value} · shap={shap.toFixed(3)}
        </span>
      </div>
      <div style={{ height: '4px', background: T.border, borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '2px',
                      transition: 'width 0.4s ease' }} />
      </div>
    </div>
  )
}

// ── Explain drawer ────────────────────────────────────────────────────────────
function ExplainDrawer({ row, onClose }) {
  const [explain, setExplain] = React.useState(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    if (!row) return
    setLoading(true)
    fetchExplanation(row.ip, row.timestamp)
      .then(d => { setExplain(d); setLoading(false) })
      .catch(() => { setExplain(null); setLoading(false) })
  }, [row])

  if (!row) return null

  const labelColor = LABEL_COLORS[row.label] || T.muted

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: '360px',
      background: '#1A1A1E', borderLeft: `1px solid ${T.border}`,
      zIndex: 1000, overflowY: 'auto', padding: '24px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px' }}>
            Why did this fire?
          </div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '13px', color: labelColor, fontWeight: 600 }}>
            {row.label?.replace(/_/g, ' ').toUpperCase()}
          </div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.accent, marginTop: '4px' }}>
            {row.ip}
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.muted, padding: '4px' }}>
          <X size={16} />
        </button>
      </div>

      {/* Scores */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '20px' }}>
        {[
          ['Risk Score', `${row.risk_score ?? '—'}`],
          ['Confidence', row.confidence != null ? `${(row.confidence * 100).toFixed(0)}%` : '—'],
          ['RF Label', row.rf_label || row.label],
          ['IF Anomaly', row.if_anomalous ? 'YES' : 'no'],
        ].map(([k, v]) => (
          <div key={k} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: '4px', padding: '10px 12px' }}>
            <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '9px', color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>{k}</div>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '14px', color: T.text, fontWeight: 600 }}>{v}</div>
          </div>
        ))}
      </div>

      {/* SHAP */}
      <div style={{ marginBottom: '8px', fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Zap size={10} /> Top feature contributions (SHAP)
      </div>

      {loading && (
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted }}>Loading…</div>
      )}
      {!loading && !explain && (
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted }}>
          No SHAP data available for this detection yet.
        </div>
      )}
      {!loading && explain?.shap_top3?.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          {explain.shap_top3.map((s, i) => <ShapBar key={i} {...s} />)}
          <div style={{ marginTop: '16px', padding: '10px 12px', background: 'rgba(45,217,255,0.05)', border: `1px solid rgba(45,217,255,0.12)`, borderRadius: '4px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, lineHeight: '1.6' }}>
            Red bars push toward this classification. Blue bars push away.
            Bar length = relative SHAP magnitude.
          </div>
        </div>
      )}

      {/* Timestamp */}
      <div style={{ marginTop: '24px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>
        {new Date(row.timestamp).toLocaleString()}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
function DetectedAttacks() {
  const [attacks, setAttacks] = useState([])
  const [selected, setSelected] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const seenRef = useRef(new Set())

  // Seed initial rows from REST, then stream deltas via WebSocket
  React.useEffect(() => {
    fetchDetections().then(data => {
      const list = (Array.isArray(data) ? data : []).reverse()
      list.forEach(d => seenRef.current.add(d.ip + d.timestamp))
      setAttacks(list.slice(0, MAX_ROWS))
    }).catch(() => {})
  }, [])

  const onDetection = useCallback((d) => {
    const key = d.ip + d.timestamp
    if (seenRef.current.has(key)) return
    seenRef.current.add(key)
    setAttacks(prev => [d, ...prev].slice(0, MAX_ROWS))
    setWsConnected(true)
  }, [])

  useDetectionStream(onDetection)

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
          Detection Log
        </div>
        <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '20px', fontWeight: 600, color: T.text, letterSpacing: '-0.01em' }}>
          Detected Attacks
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={12} style={{ color: T.danger }} />
            <span className="chart-title" style={{ margin: 0 }}>Attack events</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>
            <span style={{ width: '5px', height: '5px', background: wsConnected ? '#22c55e' : T.warning, display: 'inline-block', borderRadius: '50%' }} />
            {wsConnected ? 'live stream' : 'polling 5s'}
          </div>
        </div>

        {attacks.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Source IP</th>
                <th>Attack Type</th>
                <th>Confidence</th>
                <th>Action</th>
                <th>IF</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((attack, i) => {
                const labelColor = LABEL_COLORS[attack.label] || '#4A7FD4'
                const actionStyle = ACTION_STYLE[attack.action] || { color: T.muted, bg: 'rgba(110,113,128,0.1)', border: 'rgba(110,113,128,0.2)', label: attack.action || '—' }
                const isSelected = selected && selected.ip === attack.ip && selected.timestamp === attack.timestamp
                return (
                  <tr
                    key={`${attack.ip}-${attack.timestamp}-${i}`}
                    onClick={() => setSelected(isSelected ? null : attack)}
                    style={{ cursor: 'pointer', background: isSelected ? 'rgba(45,217,255,0.04)' : undefined }}
                  >
                    <td style={{ color: T.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px' }}>
                      {new Date(attack.timestamp).toLocaleString()}
                    </td>
                    <td style={{ color: T.accent, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px' }}>
                      {attack.ip}
                    </td>
                    <td>
                      <span style={{
                        background: labelColor + '18', color: labelColor,
                        border: `1px solid ${labelColor}30`,
                        padding: '2px 8px', borderRadius: '2px',
                        fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                      }}>
                        {attack.label?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text }}>
                      {attack.confidence != null ? `${(attack.confidence * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td>
                      <span style={{
                        background: actionStyle.bg, color: actionStyle.color,
                        border: `1px solid ${actionStyle.border}`,
                        padding: '2px 8px', borderRadius: '2px',
                        fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600,
                        letterSpacing: '0.04em',
                      }}>
                        {actionStyle.label}
                      </span>
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: attack.if_anomalous ? T.danger : T.muted }}>
                      {attack.if_anomalous == null ? '—' : attack.if_anomalous ? '⚠' : '·'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '40px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.muted }}>
            no attacks detected
          </div>
        )}
      </div>

      <ExplainDrawer row={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

export default DetectedAttacks
