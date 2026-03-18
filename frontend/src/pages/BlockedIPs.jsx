import React, { useEffect, useState } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { fetchBlockedIPs } from '../api/api'

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
    } catch (err) {
      setError(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const blockedIPs = data?.blocked_ips || []
  const stats = data?.stats || {}

  const getRiskColor = (score) => {
    if (score < 30) return 'risk-low'
    if (score < 70) return 'risk-medium'
    return 'risk-high'
  }

  const getLabelColor = (reason) => {
    const colors = {
      ddos: '#ea4335',
      port_scan: '#fbbc04',
      sql_injection: '#ff6d00',
      bruteforce: '#9c27b0',
      malware: '#f44336',
    }
    return colors[reason] || '#4285f4'
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h2 style={{ fontSize: '32px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Blocked IPs
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Automated defense actions log</p>
        </div>

        <button
          onPointerDown={loadData}
          className="header-action"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 16px',
            background: refreshing ? '#1557b0' : '#1f71e5',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            opacity: refreshing ? 0.8 : 1,
            transition: 'background 0.2s',
          }}
        >
          <RefreshCw size={16} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline - Check your API connection
        </div>
      )}

      <div className="grid-3">
        <div className="metric-card">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ color: '#ea4335', fontSize: '16px' }}>🚫</span>
            Total Blocked
          </div>
          <div className="metric-value">{stats.total_blocked || 0}</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Avg Risk Score</div>
          <div className="metric-value">
            {Number(stats.avg_risk_score || 0).toFixed(1)}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Last Blocked</div>
          <div className="metric-value" style={{ fontSize: '14px' }}>
            {stats.last_blocked_at
              ? new Date(stats.last_blocked_at).toLocaleString()
              : 'N/A'}
          </div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3 className="chart-title">Blocked IP Log</h3>
          <div style={{ fontSize: '12px', color: '#ea4335', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', background: '#ea4335', borderRadius: '50%', display: 'inline-block' }}></span>
            Auto-refresh every 5s
          </div>
        </div>

        {blockedIPs.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: '30px' }}></th>
                <th>IP Address</th>
                <th>Blocked At</th>
                <th>Reason</th>
                <th>Risk Score</th>
              </tr>
            </thead>
            <tbody>
              {blockedIPs.map((item, index) => {
                const riskScore = Number(item?.risk_score || 0)
                return (
                  <tr
                    key={index}
                    style={{
                      background: riskScore > 70 ? 'rgba(234, 67, 53, 0.05)' : 'transparent'
                    }}
                  >
                    <td style={{ color: '#ea4335' }}>🚫</td>
                    <td style={{ fontFamily: 'monospace', fontSize: '13px', color: 'var(--accent-blue)' }}>
                      {item.ip_address || item.ip || 'Unknown'}
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                      {item.blocked_at ? new Date(item.blocked_at).toLocaleString() : 'N/A'}
                    </td>
                    <td>
                      <span style={{
                        background: getLabelColor(item.reason) + '20',
                        color: getLabelColor(item.reason),
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}>
                        {item.reason || 'Unknown'}
                      </span>
                    </td>
                    <td>
                      <div className="risk-bar">
                        <span style={{ minWidth: '40px', fontSize: '13px' }}>
                          {riskScore.toFixed(1)}
                        </span>
                        <div className="risk-bar-container">
                          <div
                            className={`risk-bar-fill ${getRiskColor(riskScore)}`}
                            style={{ width: `${Math.min(riskScore, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <p style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            {error ? 'Unable to load blocked IPs' : 'No blocked IPs'}
          </p>
        )}
      </div>
    </div>
  )
}

export default BlockedIPs