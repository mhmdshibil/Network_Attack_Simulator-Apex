import React, { useEffect, useState } from 'react'
import { AlertCircle, AlertTriangle } from 'lucide-react'
import { fetchDetections } from '../api/api'

const T = {
  border:  '#232328',
  text:    '#F2F3F5',
  muted:   '#6E7180',
  accent:  '#2DD9FF',
  danger:  '#FF3B5C',
  warning: '#FFA63D',
}

const LABEL_COLORS = {
  ddos:          '#FF3B5C',
  port_scan:     '#FFA63D',
  sql_injection: '#FF6D3B',
  bruteforce:    '#9B59B6',
  malware:       '#FF3B5C',
}

const ACTION_STYLE = {
  blocked:      { color: '#FF3B5C', bg: 'rgba(255,59,92,0.1)',   border: 'rgba(255,59,92,0.25)',   label: 'BLOCK' },
  rate_limited: { color: '#FFA63D', bg: 'rgba(255,166,61,0.1)',  border: 'rgba(255,166,61,0.25)',  label: 'RATE-LIMIT' },
  monitored:    { color: '#2DD9FF', bg: 'rgba(45,217,255,0.08)', border: 'rgba(45,217,255,0.2)',   label: 'MONITOR' },
}

function DetectedAttacks() {
  const [attacks, setAttacks] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const result = await fetchDetections()
        const list = Array.isArray(result) ? result : (result?.detections || [])
        setAttacks([...list].reverse())
        setError(null)
      } catch (err) { setError(err.message) }
    }
    load()
    const iv = setInterval(load, 5000)
    return () => clearInterval(iv)
  }, [])

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

      {error && (
        <div className="demo-banner"><AlertCircle size={13} /> Backend offline — check API connection</div>
      )}

      <div className="table-container">
        <div className="table-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={12} style={{ color: T.danger }} />
            <span className="chart-title" style={{ margin: 0 }}>Attack events</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>
            <span style={{ width: '5px', height: '5px', background: T.accent, display: 'inline-block', borderRadius: '50%' }} />
            auto-refresh 5s
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
              {attacks.map((attack, i) => {
                const labelColor = LABEL_COLORS[attack.label] || '#4A7FD4'
                const actionStyle = ACTION_STYLE[attack.action] || { color: T.muted, bg: 'rgba(110,113,128,0.1)', border: 'rgba(110,113,128,0.2)', label: attack.action || '—' }
                return (
                  <tr key={i}>
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
                        {attack.label?.replace('_', ' ')}
                      </span>
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
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '40px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.muted }}>
            {error ? 'unable to load detections' : 'no attacks detected'}
          </div>
        )}
      </div>
    </div>
  )
}

export default DetectedAttacks
