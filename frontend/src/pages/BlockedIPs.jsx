import React, { useEffect, useState } from 'react'
import { AlertCircle, RefreshCw, Lock } from 'lucide-react'
import { fetchBlockedIPs } from '../api/api'
import { useCountUp } from '../hooks/useCountUp'

const T = {
  border:  '#232328',
  text:    '#F2F3F5',
  muted:   '#6E7180',
  accent:  '#2DD9FF',
  danger:  '#FF3B5C',
  warning: '#FFA63D',
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

  const blockedIPs = data?.blocked_ips || []
  const stats = data?.stats || {}

  const totalBlocked = stats.total_blocked ?? blockedIPs.length
  const countTotal = useCountUp(typeof totalBlocked === 'number' ? totalBlocked : null)

  const sevColor = (score) => score >= 70 ? T.danger : score >= 30 ? T.warning : T.accent

  const REASON_COLORS = {
    ddos: '#FF3B5C', port_scan: '#FFA63D', sql_injection: '#FF6D3B',
    bruteforce: '#9B59B6', malware: '#FF3B5C',
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
            Defense Actions
          </div>
          <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '20px', fontWeight: 600, color: T.text, letterSpacing: '-0.01em' }}>
            Blocked IPs
          </div>
        </div>
        <button
          onPointerDown={loadData}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '7px 14px',
            background: 'transparent',
            color: refreshing ? T.muted : T.text,
            border: `1px solid ${T.border}`,
            borderRadius: '2px',
            cursor: 'pointer',
            fontFamily: "'IBM Plex Mono',monospace",
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.04em',
            transition: 'border-color 0.1s, color 0.1s',
          }}
        >
          <RefreshCw size={12} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
          {refreshing ? 'refreshing' : 'refresh'}
        </button>
      </div>

      {error && (
        <div className="demo-banner"><AlertCircle size={13} /> Backend offline — check API connection</div>
      )}

      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3,1fr)', marginBottom: '16px' }}>
        <div className="metric-card risky">
          <div className="metric-label"><Lock size={11} style={{ color: T.danger }} /> Total Blocked</div>
          <div className="metric-value" style={{ color: T.danger }}>{countTotal ?? '—'}</div>
          <div className="metric-subtext">ips flagged</div>
        </div>
        <div className="metric-card detections">
          <div className="metric-label">Avg Risk Score</div>
          <div className="metric-value" style={{ color: T.warning }}>{Number(stats.avg_risk_score || 0).toFixed(1)}</div>
          <div className="metric-subtext">out of 100</div>
        </div>
        <div className="metric-card confidence">
          <div className="metric-label">Last Blocked</div>
          <div className="metric-value" style={{ color: '#4A7FD4', fontSize: '16px' }}>
            {stats.last_blocked_at ? new Date(stats.last_blocked_at).toLocaleTimeString() : '—'}
          </div>
          <div className="metric-subtext">{stats.last_blocked_at ? new Date(stats.last_blocked_at).toLocaleDateString() : 'no events'}</div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Lock size={12} style={{ color: T.danger }} />
            <span className="chart-title" style={{ margin: 0 }}>Blocked IP log</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>
            <span style={{ width: '5px', height: '5px', background: T.accent, display: 'inline-block', borderRadius: '50%' }} />
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
                const rc = REASON_COLORS[item.reason] || '#4A7FD4'
                const sc = sevColor(riskScore)
                return (
                  <tr key={i} style={{ background: riskScore > 70 ? 'rgba(255,59,92,0.04)' : 'transparent' }}>
                    <td>
                      <div style={{ width: '5px', height: '5px', background: T.danger, borderRadius: '50%' }} />
                    </td>
                    <td style={{ color: T.accent, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px' }}>
                      {item.ip_address || item.ip || 'unknown'}
                    </td>
                    <td style={{ color: T.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px' }}>
                      {item.blocked_at ? new Date(item.blocked_at).toLocaleString() : '—'}
                    </td>
                    <td>
                      <span style={{
                        background: rc + '18', color: rc, border: `1px solid ${rc}30`,
                        padding: '2px 8px', borderRadius: '2px',
                        fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600,
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                      }}>
                        {item.reason?.replace('_', ' ') || 'unknown'}
                      </span>
                    </td>
                    <td>
                      <div className="risk-bar">
                        <span style={{ minWidth: '36px', color: sc }}>{riskScore.toFixed(1)}</span>
                        <div className="risk-bar-container">
                          <div className="risk-bar-fill" style={{ width: `${Math.min(riskScore, 100)}%`, background: sc }} />
                        </div>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '40px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.muted }}>
            {error ? 'unable to load blocked IPs' : 'no blocked IPs'}
          </div>
        )}
      </div>
    </div>
  )
}

export default BlockedIPs
