/**
 * Baseline — Phase 5D: per-deployment network baseline learning.
 *
 * Shows learning/active status, a 24-hour sparkline (mean ± 1σ) per feature,
 * a live feed of baseline-deviation alerts (via WebSocket + poll), and the
 * current hour's feature statistics table. Pure inline SVG — no chart library.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { TrendingUp } from 'lucide-react'
import { useDetectionStream } from '../hooks/useDetectionStream'
import {
  fetchBaselineStatus, fetchBaselineChart, fetchBaselineHourStats, fetchBaselineAlerts,
} from '../api/api'
import './Baseline.css'

const FEATURES = [
  'packets_per_second', 'avg_request_rate', 'failed_connections', 'unique_ports',
  'bytes_per_packet', 'connection_duration', 'payload_entropy',
]

function fmtFeature(f) { return f.replace(/_/g, ' ') }

function timeAgo(ts) {
  if (!ts) return '—'
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (s < 60) return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

/* ── Sparkline: mean line (solid) + mean±std band (dashed) across 24 hours ── */
function Sparkline({ means, stds }) {
  const W = 260, H = 70, pad = 6
  const highs = means.map((m, i) => m + (stds[i] || 0))
  const lows  = means.map((m, i) => m - (stds[i] || 0))
  const allVals = [...highs, ...lows, ...means]
  const max = Math.max(...allVals, 1)
  const min = Math.min(...allVals, 0)
  const range = max - min || 1
  const x = (i) => pad + (i / 23) * (W - 2 * pad)
  const y = (v) => H - pad - ((v - min) / range) * (H - 2 * pad)

  const line = (arr) => arr.map((v, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')

  return (
    <svg className="bl-svg" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      {/* zero/baseline grid */}
      <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />
      {/* +1σ / −1σ dashed */}
      <path d={line(highs)} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1" strokeDasharray="3 3" />
      <path d={line(lows)}  fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="1" strokeDasharray="3 3" />
      {/* mean solid */}
      <path d={line(means)} fill="none" stroke="rgba(255,255,255,0.9)" strokeWidth="1.5" />
    </svg>
  )
}

export default function Baseline() {
  const [status, setStatus]   = useState(null)
  const [chart, setChart]     = useState(null)
  const [hourStats, setHourStats] = useState(null)
  const [alerts, setAlerts]   = useState([])

  const refresh = useCallback(async () => {
    const hour = new Date().getUTCHours()
    const [st, ch, hs, al] = await Promise.all([
      fetchBaselineStatus().catch(() => null),
      fetchBaselineChart().catch(() => null),
      fetchBaselineHourStats(hour).catch(() => null),
      fetchBaselineAlerts().catch(() => []),
    ])
    if (st) setStatus(st)
    if (ch) setChart(ch)
    if (hs) setHourStats(hs)
    if (Array.isArray(al)) setAlerts(al)
  }, [])

  useEffect(() => {
    let iv
    const delay = Math.random() * 2000
    const t = setTimeout(() => {
      refresh()
      iv = setInterval(refresh, 10000)
    }, delay)
    return () => { clearTimeout(t); clearInterval(iv) }
  }, [refresh])

  // Real-time baseline_alert messages — now actually received via singleton WS
  const onMessage = useCallback((msg) => {
    if (msg.type !== 'baseline_alert') return
    setAlerts(prev => [msg, ...prev].slice(0, 100))
  }, [])
  useDetectionStream(onMessage)

  const isActive = status?.status === 'active'
  const hoursActive = status?.hours_active?.length ?? 0
  const hoursLearning = status?.hours_learning?.length ?? 0
  const total = status?.total_samples ?? 0
  const minReq = status?.min_samples_required ?? 100

  return (
    <div className="baseline-page">
      <div className="bl-title">Network Baseline — Deviation Learning</div>

      {/* Status banner */}
      <div className={`bl-banner ${isActive ? 'active' : 'learning'}`}>
        <span className="bl-banner-dot" />
        {isActive ? (
          <>
            <span>Baseline Active — monitoring {hoursActive} hour{hoursActive !== 1 ? 's' : ''}. Deviation threshold: {status?.deviation_threshold ?? 3}σ</span>
            <span className="bl-banner-sub">{total} samples</span>
          </>
        ) : (
          <>
            <span>Baseline Learning in Progress — {total} samples collected. Active after {minReq} per hour. Hours active: {hoursActive}/24</span>
            <span className="bl-banner-sub">{hoursLearning} learning</span>
          </>
        )}
      </div>

      {/* Charts + deviations */}
      <div className="bl-main">
        <div className="bl-charts">
          {FEATURES.map(f => {
            const series = chart?.features?.[f]
            const means = series?.means || Array(24).fill(0)
            const stds  = series?.stds  || Array(24).fill(0)
            const maxMean = Math.max(...means, 0).toFixed(1)
            return (
              <div key={f} className="bl-chart-card">
                <div className="bl-chart-label">
                  {fmtFeature(f)}
                  <span className="bl-chart-range">peak μ {maxMean}</span>
                </div>
                <Sparkline means={means} stds={stds} />
              </div>
            )
          })}
        </div>

        {/* Recent deviations */}
        <div className="bl-side-card">
          <div className="bl-side-header">Recent Deviations</div>
          <div className="bl-alert-list">
            {alerts.length === 0 ? (
              <div className="bl-empty">
                {isActive ? 'No deviations detected.' : 'Baseline still learning — deviations flag once a hour is active.'}
              </div>
            ) : (
              alerts.slice(0, 20).map((a, i) => (
                <div key={`${a.source_ip}-${a.timestamp}-${i}`} className={`bl-alert ${a.severity}`}>
                  <div className="bl-alert-top">
                    <span className="bl-alert-ip">{a.source_ip}</span>
                    <span className={`bl-sev-badge ${a.severity}`}>{a.severity}</span>
                  </div>
                  <div className="bl-alert-features">
                    {(a.deviating_features || []).map(df =>
                      `${fmtFeature(df.feature)} (z=${df.z_score})`
                    ).join(', ')}
                  </div>
                  <div className="bl-alert-time">{timeAgo(a.timestamp)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Current-hour feature stats */}
      <div className="bl-table-card">
        <div className="bl-side-header">
          Current Hour Baseline — {hourStats ? `${String(hourStats.hour).padStart(2, '0')}:00 UTC` : '—'}
        </div>
        <table className="bl-table">
          <thead>
            <tr>
              <th>Feature</th><th>Mean</th><th>Std Dev</th><th>Samples</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {FEATURES.map(f => {
              const s = hourStats?.features?.[f]
              const active = (s?.samples ?? 0) >= minReq
              return (
                <tr key={f}>
                  <td style={{ color: 'rgba(255,255,255,0.85)' }}>{fmtFeature(f)}</td>
                  <td>{s ? s.mean : '—'}</td>
                  <td>{s ? s.std : '—'}</td>
                  <td>{s ? s.samples : 0}</td>
                  <td>
                    <span className={`bl-status-chip ${active ? 'active' : 'learning'}`}>
                      {active ? 'active' : 'learning'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
