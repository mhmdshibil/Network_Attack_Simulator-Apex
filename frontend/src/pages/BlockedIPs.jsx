import React, { useEffect, useState } from 'react'
import { AlertCircle, RefreshCw, Lock } from 'lucide-react'
import { fetchBlockedIPs } from '../api/api'
import { useCountUp } from '../hooks/useCountUp'

const T = {
  border: 'rgba(255,255,255,0.10)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

function sevBadge(score) {
  if (score >= 70) return { bg: 'rgba(255,255,255,0.14)', border: 'rgba(255,255,255,0.38)', color: '#fff',                    weight: 700, glow: '0 0 8px rgba(255,255,255,0.12)' }
  if (score >= 30) return { bg: 'rgba(255,255,255,0.07)', border: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.85)', weight: 600, glow: 'none' }
  return             { bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.55)', weight: 500, glow: 'none' }
}

function sevBarAlpha(score) {
  if (score >= 70) return { alpha: 0.95, glow: '0 0 6px rgba(255,255,255,0.4)' }
  if (score >= 30) return { alpha: 0.58, glow: 'none' }
  return             { alpha: 0.28, glow: 'none' }
}

/* All reason labels get the same monochrome badge treatment — severity from risk_score, not reason */
function reasonBadge(reason, riskScore) {
  const sb = sevBadge(riskScore)
  return sb
}

function BlockedIPs() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = async () => {
    try {
      setRefreshing(true)
      const result = await fetchBlockedIPs()
      setData(result)
      setError(null)
    } catch (err) { setError(err.message) }
    finally { setRefreshing(false) }
  }

  useEffect(() => {
    loadData()
    const iv = setInterval(loadData, 5000)
    return () => clearInterval(iv)
  }, [])

  const blockedIPs   = data?.blocked_ips || []
  const stats        = data?.stats || {}
  const totalBlocked = stats.total_blocked ?? blockedIPs.length
  const countTotal   = useCountUp(typeof totalBlocked === 'number' ? totalBlocked : null)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>
            Defense Actions
          </div>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '22px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
            Blocked IPs
          </div>
        </div>
        <button
          onPointerDown={loadData}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '8px 16px',
            background: 'rgba(255,255,255,0.06)',
            color: refreshing ? T.dim : T.text,
            border: `1px solid ${refreshing ? T.dim : 'rgba(255,255,255,0.22)'}`,
            borderRadius: '10px',
            cursor: 'pointer',
            fontFamily: "'IBM Plex Mono',monospace",
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.04em',
            transition: 'border-color 0.15s, color 0.15s, background 0.15s',
          }}
        >
          <RefreshCw size={12} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
          {refreshing ? 'refreshing' : 'refresh'}
        </button>
      </div>

      {error && <div className="demo-banner"><AlertCircle size={13} /> Backend offline — check API connection</div>}

      {/* Summary cards */}
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginBottom: '16px' }}>
        <div className="metric-card risky">
          <div className="metric-label"><Lock size={11} style={{ opacity: 0.55 }} /> Total Blocked</div>
          {/* Value weight encodes severity — many blocked IPs = bold */}
          <div className="metric-value" style={{ fontWeight: (countTotal ?? 0) > 10 ? 700 : 600 }}>{countTotal ?? '—'}</div>
          <div className="metric-subtext">ips flagged</div>
        </div>
        <div className="metric-card detections">
          <div className="metric-label">Avg Risk Score</div>
          <div className="metric-value">{Number(stats.avg_risk_score || 0).toFixed(1)}</div>
          <div className="metric-subtext">out of 100</div>
        </div>
        <div className="metric-card confidence">
          <div className="metric-label">Last Blocked</div>
          <div className="metric-value" style={{ fontSize: stats.last_blocked_at ? '18px' : '30px' }}>
            {stats.last_blocked_at ? new Date(stats.last_blocked_at).toLocaleTimeString() : '—'}
          </div>
          <div className="metric-subtext">{stats.last_blocked_at ? new Date(stats.last_blocked_at).toLocaleDateString() : 'no events'}</div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Lock size={12} style={{ opacity: 0.40 }} />
            <span className="chart-title" style={{ margin: 0 }}>Blocked IP log</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim }}>
            <span style={{ width: '6px', height: '6px', background: 'rgba(255,255,255,0.5)', display: 'inline-block', borderRadius: '50%', boxShadow: '0 0 4px rgba(255,255,255,0.4)' }} />
            auto-refresh 5s
          </div>
        </div>

        {blockedIPs.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '24px' }}></th>
                <th>IP Address</th>
                <th>Blocked At</th>
                <th>Reason</th>
                <th>Risk Score</th>
              </tr>
            </thead>
            <tbody>
              {blockedIPs.map((item, i) => {
                const riskScore = Number(item?.risk_score || 0)
                const sb  = sevBadge(riskScore)
                const bar = sevBarAlpha(riskScore)
                return (
                  <tr key={i} style={{ background: riskScore > 70 ? 'rgba(255,255,255,0.025)' : 'transparent' }}>
                    <td>
                      <div style={{ width: '5px', height: '5px', background: riskScore > 70 ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.3)', borderRadius: '50%', boxShadow: riskScore > 70 ? '0 0 4px rgba(255,255,255,0.5)' : 'none' }} />
                    </td>
                    <td style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', fontWeight: 600, color: T.text }}>
                      {item.ip_address || item.ip || 'unknown'}
                    </td>
                    <td style={{ color: T.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px' }}>
                      {item.blocked_at ? new Date(item.blocked_at).toLocaleString() : '—'}
                    </td>
                    <td>
                      <span style={{
                        background: sb.bg, color: sb.color, border: `1px solid ${sb.border}`,
                        padding: '3px 9px', borderRadius: '6px',
                        fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: sb.weight,
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                        boxShadow: sb.glow,
                      }}>
                        {item.reason?.replace('_', ' ') || 'unknown'}
                      </span>
                    </td>
                    <td>
                      <div className="risk-bar">
                        <span style={{ minWidth: '36px', color: T.text, fontWeight: sb.weight, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px' }}>{riskScore.toFixed(1)}</span>
                        <div className="risk-bar-container">
                          <div className="risk-bar-fill" style={{ width: `${Math.min(riskScore, 100)}%`, background: `rgba(255,255,255,${bar.alpha})`, boxShadow: bar.glow }} />
                        </div>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.dim }}>
            {error ? 'unable to load blocked IPs' : 'no blocked IPs'}
          </div>
        )}
      </div>
    </div>
  )
}

export default BlockedIPs
