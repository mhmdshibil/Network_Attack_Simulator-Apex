/**
 * DetectedAttacks — Phase 1 + 5 + 8
 * WebSocket stream → polling fallback
 * Click row → SHAP drawer with MITRE badge + LLM summary
 * Full monochrome design: severity via weight/glow, no hue
 */
import React, { useCallback, useState, useRef } from 'react'
import { AlertTriangle, X, Zap, Brain } from 'lucide-react'
import { fetchDetections, fetchExplanation, generateIncidentSummary } from '../api/api'
import { useDetectionStream } from '../hooks/useDetectionStream'
import { useAuth } from '../context/AuthContext'

const T = {
  bg:     '#000000',
  panel:  '#0a0a0a',
  border: 'rgba(255,255,255,0.10)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

const panelBg = `linear-gradient(${T.panel}, ${T.panel}) padding-box, linear-gradient(135deg, rgba(255,255,255,0.13) 0%, rgba(255,255,255,0.04) 100%) border-box`

/* Severity hierarchy — no hue, only weight + alpha */
function labelBadge(label) {
  const critical = ['ddos', 'malware']
  const elevated = ['bruteforce', 'sql_injection']
  if (critical.includes(label)) return { bg: 'rgba(255,255,255,0.14)', border: 'rgba(255,255,255,0.38)', color: '#fff',                    weight: 700, shadow: '0 0 8px rgba(255,255,255,0.12)' }
  if (elevated.includes(label)) return { bg: 'rgba(255,255,255,0.08)', border: 'rgba(255,255,255,0.24)', color: 'rgba(255,255,255,0.88)', weight: 600, shadow: 'none' }
  /* port_scan, unknown_anomaly, others */
  return { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.15)', color: 'rgba(255,255,255,0.65)', weight: 500, shadow: 'none' }
}

function actionBadge(action) {
  if (action === 'blocked')      return { bg: 'rgba(255,255,255,0.13)', border: 'rgba(255,255,255,0.38)', color: '#fff',                    weight: 700, label: 'BLOCK',      shadow: '0 0 8px rgba(255,255,255,0.10)' }
  if (action === 'rate_limited') return { bg: 'rgba(255,255,255,0.07)', border: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.85)', weight: 600, label: 'RATE-LIMIT', shadow: 'none' }
  return { bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.55)', weight: 500, label: action ? action.toUpperCase() : 'MONITOR', shadow: 'none' }
}

function severityWeight(label) {
  if (['ddos', 'malware'].includes(label)) return 700
  if (['bruteforce', 'sql_injection'].includes(label)) return 600
  return 400
}

const MAX_ROWS = 200

/* ── SHAP bar ────────────────────────────────────────────────── */
function ShapBar({ feature, value, shap }) {
  const pct    = Math.min(Math.abs(shap) * 800, 100)
  /* pushing toward classification → brighter; pushing away → dimmer */
  const alpha  = shap > 0 ? 0.88 : 0.42
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, fontWeight: shap > 0 ? 600 : 400 }}>
          {(shap > 0 ? '↑ ' : '↓ ') + feature.replace(/_/g, ' ')}
        </span>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>
          val={value} · {shap.toFixed(3)}
        </span>
      </div>
      <div style={{ height: '4px', background: 'rgba(255,255,255,0.07)', borderRadius: '2px', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: `rgba(255,255,255,${alpha})`,
          borderRadius: '2px',
          transition: 'width 0.4s ease',
          boxShadow: shap > 0 ? '0 0 6px rgba(255,255,255,0.25)' : 'none',
        }} />
      </div>
    </div>
  )
}

/* ── Explain drawer ──────────────────────────────────────────── */
function ExplainDrawer({ row, onClose }) {
  const [explain, setExplain] = React.useState(null)
  const [loading, setLoading] = React.useState(true)
  const [summary, setSummary] = React.useState(null)
  const [summaryLoading, setSummaryLoading] = React.useState(false)
  const { llmConfigured } = useAuth()

  React.useEffect(() => {
    if (!row) return
    setLoading(true)
    setSummary(null)
    fetchExplanation(row.ip, row.timestamp)
      .then(d => { setExplain(d); setLoading(false) })
      .catch(() => { setExplain(null); setLoading(false) })
  }, [row])

  const handleSummarize = async () => {
    if (!row || summaryLoading) return
    setSummaryLoading(true)
    const result = await generateIncidentSummary(row)
    setSummary(result)
    setSummaryLoading(false)
  }

  if (!row) return null

  const lb = labelBadge(row.label)

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: '380px',
      background: '#050505',
      borderLeft: '1px solid rgba(255,255,255,0.12)',
      zIndex: 1000,
      overflowY: 'auto',
      padding: '26px 24px',
      boxShadow: '-8px 0 40px rgba(0,0,0,0.7)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '22px' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '7px' }}>
            Why did this fire?
          </div>
          <div style={{
            fontFamily: "'IBM Plex Mono',monospace", fontSize: '13px', color: T.text, fontWeight: lb.weight,
            letterSpacing: '0.02em', textTransform: 'uppercase',
          }}>
            {row.label?.replace(/_/g, ' ').toUpperCase()}
          </div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.muted, marginTop: '4px', fontWeight: 600 }}>
            {row.ip}
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.dim, padding: '4px', lineHeight: 0 }}>
          <X size={16} />
        </button>
      </div>

      {/* MITRE badge */}
      {row.mitre && row.mitre.technique_id !== 'T0000' && (
        <div style={{ marginBottom: '18px', padding: '12px 14px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '12px' }}>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '9px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>MITRE ATT&CK</div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.text, fontWeight: 700, letterSpacing: '0.02em' }}>
            {row.mitre.technique_id}
            <span style={{ fontWeight: 400, color: T.muted }}> · {row.mitre.technique}</span>
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '11px', color: T.dim, marginTop: '3px' }}>
            Tactic: {row.mitre.tactic}
          </div>
        </div>
      )}

      {/* Score grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '22px' }}>
        {[
          ['Risk Score', `${row.risk_score ?? '—'}`],
          ['Confidence', row.confidence != null ? `${(row.confidence * 100).toFixed(0)}%` : '—'],
          ['RF Label',   row.rf_label || row.label],
          ['IF Anomaly', row.if_anomalous ? 'YES' : 'no'],
        ].map(([k, v]) => {
          const isCritical = k === 'IF Anomaly' && v === 'YES'
          return (
            <div key={k} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: '10px', padding: '11px 13px' }}>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '9px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>{k}</div>
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '14px', color: isCritical ? '#fff' : T.text, fontWeight: isCritical ? 700 : 600, letterSpacing: '-0.01em' }}>{v}</div>
            </div>
          )
        })}
      </div>

      {/* SHAP */}
      <div style={{ marginBottom: '8px', fontFamily: "'Inter', sans-serif", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <Zap size={10} /> Top feature contributions (SHAP)
      </div>

      {loading && <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.dim }}>Loading…</div>}
      {!loading && !explain && (
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.dim }}>No SHAP data for this detection.</div>
      )}
      {!loading && explain?.shap_top3?.length > 0 && (
        <div style={{ marginTop: '12px' }}>
          {explain.shap_top3.map((s, i) => <ShapBar key={i} {...s} />)}
          <div style={{ marginTop: '14px', padding: '10px 12px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.10)', borderRadius: '8px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, lineHeight: '1.6' }}>
            Bright bars push toward this classification · Dim bars push away.
            Bar length = relative SHAP magnitude.
          </div>
        </div>
      )}

      {/* LLM summary */}
      <div style={{ marginTop: '22px' }}>
        <div style={{ marginBottom: '10px', fontFamily: "'Inter', sans-serif", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Brain size={10} /> Analyst Summary (Claude AI)
        </div>

        {!llmConfigured && (
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, padding: '9px 12px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px' }}>
            not configured — set <span style={{ color: T.text, fontWeight: 600 }}>ANTHROPIC_API_KEY</span> to enable
          </div>
        )}

        {llmConfigured && !summary && !summaryLoading && (
          <button
            onClick={handleSummarize}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.22)', borderRadius: '10px', color: T.text, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', padding: '10px 14px', cursor: 'pointer', width: '100%', justifyContent: 'center', fontWeight: 600, transition: 'background 0.15s' }}
          >
            <Brain size={12} /> Generate Incident Summary
          </button>
        )}
        {llmConfigured && summaryLoading && (
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted, padding: '8px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ display: 'inline-block', width: '7px', height: '7px', borderRadius: '50%', background: '#fff', animation: 'pulse-glow 1s infinite' }} />
            Consulting Claude…
          </div>
        )}
        {llmConfigured && summary && !summaryLoading && (
          <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '10px', padding: '14px' }}>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '12px', color: T.text, lineHeight: '1.6', margin: '0 0 10px 0', maxWidth: 'none' }}>
              {summary.summary}
            </p>
            {summary.recommendation && (
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.10)', paddingTop: '8px', marginTop: '8px' }}>
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.muted, textTransform: 'uppercase', letterSpacing: '0.10em' }}>Recommendation: </span>
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '12px', color: T.text, fontWeight: 600 }}>{summary.recommendation}</span>
              </div>
            )}
            {summary.cached && (
              <div style={{ marginTop: '6px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.dim }}>cached</div>
            )}
          </div>
        )}
      </div>

      <div style={{ marginTop: '26px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>
        {new Date(row.timestamp).toLocaleString()}
      </div>
    </div>
  )
}

/* ── Main ────────────────────────────────────────────────────── */
function DetectedAttacks() {
  const [attacks, setAttacks] = useState([])
  const [selected, setSelected] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const seenRef = useRef(new Set())

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
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: 'rgba(255,255,255,0.28)', textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>
          Detection Log
        </div>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '22px', fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>
          Detected Attacks
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={12} style={{ color: 'rgba(255,255,255,0.40)' }} />
            <span className="chart-title" style={{ margin: 0 }}>Attack events</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: 'rgba(255,255,255,0.40)' }}>
            <span style={{
              width: '6px', height: '6px',
              background: wsConnected ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.35)',
              display: 'inline-block', borderRadius: '50%',
              boxShadow: wsConnected ? '0 0 5px rgba(255,255,255,0.5)' : 'none',
            }} />
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
                <th>MITRE</th>
                <th>Confidence</th>
                <th>Action</th>
                <th>IF</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((attack, i) => {
                const lb = labelBadge(attack.label)
                const ab = actionBadge(attack.action)
                const isSelected = selected && selected.ip === attack.ip && selected.timestamp === attack.timestamp
                const w = severityWeight(attack.label)
                return (
                  <tr
                    key={`${attack.ip}-${attack.timestamp}-${i}`}
                    onClick={() => setSelected(isSelected ? null : attack)}
                    style={{
                      cursor: 'pointer',
                      background: isSelected ? 'rgba(255,255,255,0.05)' : undefined,
                      boxShadow: isSelected ? 'inset 0 0 0 1px rgba(255,255,255,0.12)' : 'none',
                    }}
                  >
                    <td style={{ color: 'rgba(255,255,255,0.45)', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px' }}>
                      {new Date(attack.timestamp).toLocaleString()}
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', fontWeight: 600, color: '#fff' }}>
                      {attack.ip}
                    </td>
                    <td>
                      <span style={{
                        background: lb.bg, color: lb.color, border: `1px solid ${lb.border}`,
                        padding: '3px 9px', borderRadius: '6px',
                        fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: lb.weight,
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                        boxShadow: lb.shadow,
                      }}>
                        {attack.label?.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      {attack.mitre?.technique_id && attack.mitre.technique_id !== 'T0000'
                        ? <span className="mitre-badge">{attack.mitre.technique_id}</span>
                        : <span style={{ color: 'rgba(255,255,255,0.22)', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px' }}>—</span>
                      }
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: '#fff', fontWeight: w }}>
                      {attack.confidence != null ? `${(attack.confidence * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td>
                      <span style={{
                        background: ab.bg, color: ab.color, border: `1px solid ${ab.border}`,
                        padding: '3px 9px', borderRadius: '6px',
                        fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: ab.weight,
                        letterSpacing: '0.04em', boxShadow: ab.shadow,
                      }}>
                        {ab.label}
                      </span>
                    </td>
                    <td style={{
                      fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px',
                      color: attack.if_anomalous ? '#fff' : 'rgba(255,255,255,0.25)',
                      fontWeight: attack.if_anomalous ? 700 : 400,
                    }}>
                      {attack.if_anomalous == null ? '—' : attack.if_anomalous ? '⚠' : '·'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: 'rgba(255,255,255,0.30)' }}>
            no attacks detected
          </div>
        )}
      </div>

      <ExplainDrawer row={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

export default DetectedAttacks
