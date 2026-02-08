import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import { usePolling } from '../hooks/usePolling'

function BlockedIPs() {
  const { data, error, refetch } = usePolling('http://127.0.0.1:8000/api/blocked_ips')
  
  const blockedIPs = data?.blocked_ips || []
  const stats = data?.stats || {}

  const getRiskColor = (score) => {
    if (score < 30) return 'risk-low'
    if (score < 70) return 'risk-medium'
    return 'risk-high'
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
          onClick={refetch}
          className="header-action"
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px',
            padding: '8px 16px',
            background: '#1f71e5',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          <RefreshCw size={16} />
          Refresh
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
          <div className="metric-value">{(stats.avg_risk_score || 0).toFixed(1)}</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-label">Last Blocked</div>
          <div className="metric-value" style={{ fontSize: '14px' }}>
            {stats.last_blocked_at ? new Date(stats.last_blocked_at).toLocaleString() : 'N/A'}
          </div>
        </div>
      </div>

      <div className="table-container">
        <div className="table-header">
          <h3 className="chart-title">Blocked IP Log</h3>
          <div style={{ fontSize: '12px', color: '#ea4335', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', background: '#ea4335', borderRadius: '50%' }}></span>
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
                <th>Reason / Attack Type</th>
                <th>Risk Score at Block</th>
              </tr>
            </thead>
            <tbody>
              {blockedIPs.map((item, index) => (
                <tr key={index} style={{ background: item.risk_score > 70 ? 'rgba(234, 67, 53, 0.05)' : 'transparent' }}>
                  <td style={{ cursor: 'pointer', color: '#ea4335' }}>🚫</td>
                  <td style={{ fontFamily: 'monospace', fontSize: '13px', color: 'var(--accent-blue)' }}>
                    {item.ip_address}
                  </td>
                  <td>{new Date(item.blocked_at).toLocaleString()}</td>
                  <td style={{ color: 'var(--accent-red)' }}>{item.reason}</td>
                  <td>
                    <div className="risk-bar">
                      <span style={{ minWidth: '40px' }}>{item.risk_score.toFixed(1)}</span>
                      <div className="risk-bar-container">
                        <div 
                          className={`risk-bar-fill ${getRiskColor(item.risk_score)}`}
                          style={{ width: `${Math.min(item.risk_score, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
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
