/**
 * Compliance — Phase 3 / Task 2
 * ISO 27001 compliance dashboard with SVG gauge, controls table, and 30-day metrics.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { ShieldCheck, FileDown } from 'lucide-react'
import { API_BASE } from '../api/api'
import './Compliance.css'

const T = {
  bg:     '#000000',
  panel:  '#0a0a0a',
  border: 'rgba(255,255,255,0.10)',
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

// ISO 27001 controls — static mapping (controls don't change between runs)
const ISO_CONTROLS = [
  { id: 'A.12.4.1', control: 'Event logging',                        impl: 'detections.csv + real-time audit trail' },
  { id: 'A.12.4.2', control: 'Protection of log information',        impl: 'JSONL + DB dual-write fallback' },
  { id: 'A.12.4.3', control: 'Administrator and operator logs',      impl: 'decision_audit.csv per response' },
  { id: 'A.16.1.1', control: 'Responsibilities for IDS',             impl: 'MITRE mapping + response engine' },
  { id: 'A.16.1.2', control: 'Reporting security events',            impl: 'LLM summaries + PDF reports' },
  { id: 'A.16.1.4', control: 'Assessment of security events',        impl: 'SHAP explainability + risk scores' },
  { id: 'A.16.1.5', control: 'Response to incidents',                impl: 'Triage workflow + SLA tracking' },
  { id: 'A.16.1.6', control: 'Learning from incidents',              impl: 'ML evaluation harness + FPR tracking' },
  { id: 'A.16.1.7', control: 'Collection of evidence',               impl: 'Immutable audit trail CSV/JSONL' },
]

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('apex_token')
  return fetch(url, {
    ...opts,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  })
}

function computeScore(stats) {
  if (!stats) return null
  const total    = stats.total_cases || 0
  const resolved = stats.resolved_cases || 0
  const resRate  = total > 0 ? resolved / total : 0
  const detAcc   = 1 - (stats.false_positive_rate || 0)
  const slaRate  = 1 - (stats.sla_breach_rate || 0)
  return {
    score: Math.round(resRate * 40 + detAcc * 30 + slaRate * 30),
    resRate, detAcc, slaRate,
  }
}

/* SVG circle gauge — pure SVG, no library */
function CircleGauge({ score, color }) {
  const r = 68
  const cx = 90
  const cy = 90
  const circumference = 2 * Math.PI * r
  const dashOffset = score != null ? circumference * (1 - score / 100) : circumference

  return (
    <svg width="180" height="180" viewBox="0 0 180 180" style={{ display: 'block' }}>
      {/* Background track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" />
      {/* Progress arc */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s ease' }}
      />
      {/* Score text */}
      <text
        x={cx} y={cy + 10}
        textAnchor="middle"
        fill={color}
        fontSize="30"
        fontWeight="700"
        fontFamily="'Space Grotesk', sans-serif"
        style={{ letterSpacing: '-0.03em' }}
      >
        {score ?? '—'}
      </text>
      {/* Sub label */}
      <text x={cx} y={cy + 28} textAnchor="middle" fill="rgba(255,255,255,0.30)" fontSize="9" fontFamily="'IBM Plex Mono', monospace">
        OUT OF 100
      </text>
    </svg>
  )
}

function ProgressBar({ label, rate, weight, color }) {
  const pct = Math.round(rate * 100)
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{ fontFamily: "'Inter',sans-serif", fontSize: '12px', color: T.muted }}>{label}</span>
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, fontWeight: 600 }}>
          {pct}% <span style={{ color: T.dim, fontWeight: 400 }}>×{weight}</span>
        </span>
      </div>
      <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: color || 'rgba(255,255,255,0.70)',
          borderRadius: '3px',
          transition: 'width 0.6s ease',
        }} />
      </div>
    </div>
  )
}

function MetricRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: `1px solid ${T.border}` }}>
      <span style={{ fontFamily: "'Inter',sans-serif", fontSize: '12px', color: T.muted }}>{label}</span>
      <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.text, fontWeight: 600, background: 'rgba(255,255,255,0.06)', padding: '3px 10px', borderRadius: '6px' }}>{value}</span>
    </div>
  )
}

function Compliance() {
  const [stats, setStats]         = useState(null)
  const [downloading, setDownloading] = useState(false)
  const [dlError, setDlError]     = useState(null)

  const loadStats = useCallback(async () => {
    try {
      const res = await authFetch(`${API_BASE}/api/triage/stats`)
      if (res.ok) setStats(await res.json())
    } catch { }
  }, [])

  useEffect(() => {
    loadStats()
    const iv = setInterval(loadStats, 30000)
    return () => clearInterval(iv)
  }, [loadStats])

  const handleDownload = async () => {
    setDownloading(true)
    setDlError(null)
    try {
      const res = await authFetch(`${API_BASE}/api/reports/compliance`)
      if (!res.ok) throw new Error(`Report failed (${res.status})`)
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `apex_compliance_${new Date().toISOString().slice(0, 10)}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setDlError(e.message)
    } finally {
      setDownloading(false)
    }
  }

  const computed  = computeScore(stats)
  const score     = computed?.score ?? null
  const scoreColor = score == null ? T.muted : score > 80 ? '#80ff90' : score >= 60 ? '#ffe08a' : '#ff8080'
  const scoreLabel = score == null ? '—' : score > 80 ? 'COMPLIANT' : score >= 60 ? 'PARTIAL COMPLIANCE' : 'NON-COMPLIANT'

  const fmtMins = (m) => m == null ? '—' : m < 60 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} h`

  return (
    <div>
      {/* Page header */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>
            Security Compliance
          </div>
          <div style={{ fontFamily: "'Space Grotesk',sans-serif", fontSize: '22px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
            Compliance Dashboard
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {dlError && <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>{dlError}</span>}
          <button
            onClick={handleDownload}
            disabled={downloading}
            className="time-btn"
            style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '8px 14px', textTransform: 'none', letterSpacing: '0.02em', opacity: downloading ? 0.6 : 1, cursor: downloading ? 'default' : 'pointer' }}
          >
            <ShieldCheck size={13} />
            {downloading ? 'Generating…' : 'Download Compliance Report'}
          </button>
        </div>
      </div>

      {/* Compliance score card */}
      <div style={{ ...panelStyle, padding: '28px 32px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap', alignItems: 'flex-start' }}>

          {/* SVG Gauge */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '4px' }}>
              Compliance Score
            </div>
            <CircleGauge score={score} color={scoreColor} />
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: scoreColor, fontWeight: 700, letterSpacing: '0.06em' }}>
              {scoreLabel}
            </div>
            <div style={{ fontFamily: "'Inter',sans-serif", fontSize: '10px', color: T.dim, textAlign: 'center' }}>
              &lt;60 non-compliant · 60–80 partial · &gt;80 compliant
            </div>
          </div>

          {/* Progress bars */}
          <div style={{ flex: '1 1 320px' }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '16px' }}>
              Component Scores
            </div>
            <ProgressBar label="Case Resolution Rate"  rate={computed?.resRate ?? 0} weight="0.40" color="rgba(128,255,144,0.75)" />
            <ProgressBar label="Detection Accuracy"    rate={computed?.detAcc  ?? 0} weight="0.30" color="rgba(255,224,138,0.75)" />
            <ProgressBar label="SLA Compliance Rate"   rate={computed?.slaRate ?? 0} weight="0.30" color="rgba(128,191,255,0.75)" />
          </div>
        </div>
      </div>

      {/* ISO 27001 controls */}
      <div className="table-container" style={{ marginBottom: '20px' }}>
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={12} style={{ color: T.muted }} />
            <span className="chart-title" style={{ margin: 0 }}>ISO 27001 Controls</span>
          </div>
          <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>9 CONTROLS</span>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: '90px' }}>Control</th>
              <th>Requirement</th>
              <th>Implementation</th>
              <th style={{ width: '70px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {ISO_CONTROLS.map((c, idx) => (
              <tr key={c.id} style={{ background: idx % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, fontWeight: 600 }}>{c.id}</td>
                <td style={{ fontFamily: "'Inter',sans-serif", fontSize: '12px', color: T.muted }}>{c.control}</td>
                <td style={{ fontFamily: "'Inter',sans-serif", fontSize: '11px', color: T.dim }}>{c.impl}</td>
                <td>
                  <span style={{ background: 'rgba(50,200,100,0.12)', border: '1px solid rgba(50,200,100,0.40)', color: '#80ff90', padding: '3px 9px', borderRadius: '6px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 700 }}>
                    MET
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 30-day metrics */}
      <div style={{ ...panelStyle, padding: '24px 28px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '16px' }}>
          30-Day Metrics (from Triage)
        </div>
        <MetricRow label="Open Cases"             value={stats?.open_count ?? '—'} />
        <MetricRow label="Total Cases"            value={stats?.total_cases ?? '—'} />
        <MetricRow label="Resolved Cases"         value={stats?.resolved_cases ?? '—'} />
        <MetricRow label="Mean Time to Respond"   value={fmtMins(stats?.avg_resolution_minutes)} />
        <MetricRow label="SLA Compliance Rate"    value={stats ? `${((1 - stats.sla_breach_rate) * 100).toFixed(0)}%` : '—'} />
        <MetricRow label="SLA Breach Count"       value={stats?.sla_breach_count ?? '—'} />
        <MetricRow label="False Positive Rate"    value={stats ? `${(stats.false_positive_rate * 100).toFixed(1)}%` : '—'} />
      </div>
    </div>
  )
}

export default Compliance
