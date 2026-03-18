import React, { useEffect, useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { fetchDetections } from '../api/api'

function DetectedAttacks() {
  const [attacks, setAttacks] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchDetections()
        // API returns a plain array directly
        const list = Array.isArray(result) ? result : (result?.detections || [])
        setAttacks([...list].reverse()) // most recent first
        setError(null)
      } catch (err) {
        setError(err.message)
      }
    }

    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  const getActionBadge = (action) => {
    if (action === 'blocked') return { label: 'Blocked', color: '#ea4335' }
    if (action === 'rate_limited') return { label: 'Rate Limited', color: '#fbbc04' }
    if (action === 'monitored') return { label: 'Monitored', color: '#34a853' }
    return { label: action || 'Unknown', color: '#5f6368' }
  }

  const getLabelColor = (label) => {
    const colors = {
      ddos: '#ea4335',
      port_scan: '#fbbc04',
      sql_injection: '#ff6d00',
      bruteforce: '#9c27b0',
      malware: '#f44336',
    }
    return colors[label] || '#4285f4'
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
            <span style={{ width: '8px', height: '8px', background: '#ea4335', borderRadius: '50%', display: 'inline-block' }}></span>
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
              </tr>
            </thead>
            <tbody>
              {attacks.map((attack, index) => {
                const badge = getActionBadge(attack.action)
                return (
                  <tr key={index}>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                      {new Date(attack.timestamp).toLocaleString()}
                    </td>
                    <td style={{ color: 'var(--accent-blue)', fontFamily: 'monospace', fontSize: '13px' }}>
                      {attack.ip}
                    </td>
                    <td>
                      <span style={{
                        background: getLabelColor(attack.label) + '20',
                        color: getLabelColor(attack.label),
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}>
                        {attack.label}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        background: badge.color + '20',
                        color: badge.color,
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}>
                        {badge.label}
                      </span>
                    </td>
                  </tr>
                )
              })}
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