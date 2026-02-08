import React from 'react'
import { AlertCircle } from 'lucide-react'
import { usePolling } from '../hooks/usePolling'

function DetectedAttacks() {
  const { data, error } = usePolling('http://127.0.0.1:8000/api/detections')

  const attacks = data?.detections || []

  const getRiskColor = (score) => {
    if (score < 30) return 'risk-low'
    if (score < 70) return 'risk-medium'
    return 'risk-high'
  }

  const getActionBadge = (action) => {
    if (action === 'logged') return 'badge-logged'
    if (action === 'quarantined') return 'badge-quarantined'
    return 'badge-blocked'
  }

  const getConfidenceBar = (confidence) => {
    return (
      <div className="risk-bar">
        <span style={{ minWidth: '30px' }}>{confidence.toFixed(1)}%</span>
        <div className="risk-bar-container">
          <div
            className="risk-bar-fill"
            style={{
              width: `${Math.min(confidence, 100)}%`,
              background: confidence > 70 ? '#34a853' : confidence > 40 ? '#fbbc04' : '#ea4335',
            }}
          ></div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '32px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Detected Attacks
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Real-time attack detection log</p>
      </div>

      {error && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline - Check your API connection
        </div>
      )}

      <div className="table-container">
        <div className="table-header">
          <h3 className="chart-title">Detection Log</h3>
          <div style={{ fontSize: '12px', color: '#ea4335', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', background: '#ea4335', borderRadius: '50%' }}></span>
            Auto-refresh every 5s
          </div>
        </div>

        {attacks.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Source IP</th>
                <th>Attack Type</th>
                <th>Action</th>
                <th>Risk Score</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {attacks.map((attack, index) => (
                <tr key={index} style={{ background: attack.risk_score > 70 ? 'rgba(234, 67, 53, 0.05)' : 'transparent' }}>
                  <td>{new Date(attack.timestamp).toLocaleString()}</td>
                  <td style={{ color: 'var(--accent-blue)', fontFamily: 'monospace', fontSize: '13px' }}>
                    {attack.source_ip}
                  </td>
                  <td>{attack.attack_type}</td>
                  <td>
                    <span className={`badge ${getActionBadge(attack.action)}`}>
                      {attack.action}
                    </span>
                  </td>
                  <td>
                    <div className="risk-bar">
                      <span style={{ minWidth: '30px' }}>{attack.risk_score.toFixed(1)}</span>
                      <div className="risk-bar-container">
                        <div
                          className={`risk-bar-fill ${getRiskColor(attack.risk_score)}`}
                          style={{ width: `${Math.min(attack.risk_score, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td>{getConfidenceBar(attack.confidence)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            {error ? 'Unable to load detections' : 'No attacks detected'}
          </p>
        )}
      </div>
    </div>
  )
}

export default DetectedAttacks

