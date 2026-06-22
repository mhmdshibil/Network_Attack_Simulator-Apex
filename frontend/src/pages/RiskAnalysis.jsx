import React, { useState, useEffect } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import { fetchTopAttackers } from '../api/api'

const T = {
  border:  '#232328',
  text:    '#F2F3F5',
  muted:   '#6E7180',
  accent:  '#2DD9FF',
  danger:  '#FF3B5C',
  warning: '#FFA63D',
}

function RiskAnalysis() {
  const [expandedIP, setExpandedIP] = useState(null)
  const [timeWindow, setTimeWindow] = useState('24h')
  const [risks, setRisks] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const result = await fetchTopAttackers()
        const attackers = result?.attackers || []
        const computed = attackers.map(attacker => {
          const riskScore  = Math.min((attacker.count / 200) * 100, 100)
          const confidence = Math.min(50 + attacker.count * 0.5, 100)
          let severity = 'Low'
          if (riskScore >= 70) severity = 'High'
          else if (riskScore >= 30) severity = 'Medium'
          return {
            ip: attacker.ip,
            risk_score: parseFloat(riskScore.toFixed(1)),
            confidence: parseFloat(confidence.toFixed(1)),
            severity,
            attack_count: attacker.count,
            first_seen: attacker.first_seen,
            last_seen: attacker.last_seen,
          }
        }).sort((a, b) => b.risk_score - a.risk_score)
        setRisks(computed)
        setError(null)
      } catch (err) { setError(err.message) }
    }
    load()
    const iv = setInterval(load, 5000)
    return () => clearInterval(iv)
  }, [timeWindow])

  const sevColor = (score) => score >= 70 ? T.danger : score >= 30 ? T.warning : T.accent

  return (
    <div>
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
          Intelligence
        </div>
        <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '20px', fontWeight: 600, color: T.text, letterSpacing: '-0.01em' }}>
          Risk Analysis
        </div>
      </div>

      {error && (
        <div className="demo-banner"><AlertCircle size={13} /> Backend offline — check API connection</div>
      )}

      <div className="table-container">
        <div className="table-header">
          <div>
            <span className="chart-title" style={{ margin: 0 }}>Risk scores by IP</span>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, marginTop: '3px' }}>click row to expand</div>
          </div>
          <div style={{ display: 'flex', gap: '4px' }}>
            {['1h', '24h'].map(w => (
              <button key={w} onClick={() => setTimeWindow(w)} className={`time-btn ${timeWindow === w ? 'active' : ''}`}>{w}</button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '8px 16px 8px 20px', borderBottom: `1px solid ${T.border}` }}>
          <div style={{ width: '16px' }} />
          <div style={{ minWidth: '140px', fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>IP Address</div>
          <div style={{ minWidth: '140px', fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Risk Score</div>
          <div style={{ minWidth: '80px',  fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Severity</div>
          <div style={{ minWidth: '150px', fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Confidence</div>
          <div style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Events</div>
        </div>

        {risks.length > 0 ? (
          <div className="expandable-table">
            {risks.map((risk, i) => {
              const sc = sevColor(risk.risk_score)
              const isOpen = expandedIP === i
              return (
                <div key={i} className="expandable-row-wrapper">
                  <div
                    className="expandable-row"
                    onClick={() => setExpandedIP(isOpen ? null : i)}
                    style={{ borderLeft: risk.risk_score >= 70 ? `2px solid rgba(255,59,92,0.4)` : '2px solid transparent' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '10px 16px 10px 18px' }}>
                      <ChevronDown size={13} style={{ color: T.muted, flexShrink: 0, transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
                      <div style={{ minWidth: '140px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.accent }}>{risk.ip}</div>
                      <div style={{ minWidth: '140px' }}>
                        <div className="risk-bar">
                          <span style={{ minWidth: '36px', color: sc }}>{risk.risk_score.toFixed(1)}</span>
                          <div className="risk-bar-container">
                            <div className="risk-bar-fill" style={{ width: `${Math.min(risk.risk_score, 100)}%`, background: sc }} />
                          </div>
                        </div>
                      </div>
                      <div style={{ minWidth: '80px' }}>
                        <span style={{
                          background: sc + '18', color: sc, border: `1px solid ${sc}30`,
                          padding: '2px 8px', borderRadius: '2px',
                          fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600,
                          textTransform: 'uppercase', letterSpacing: '0.04em',
                        }}>{risk.severity}</span>
                      </div>
                      <div style={{ minWidth: '150px' }}>
                        <div className="risk-bar">
                          <span style={{ minWidth: '36px', color: T.muted }}>{risk.confidence.toFixed(0)}%</span>
                          <div className="risk-bar-container">
                            <div className="risk-bar-fill" style={{ width: `${Math.min(risk.confidence, 100)}%`, background: risk.confidence > 70 ? T.accent : risk.confidence > 40 ? T.warning : T.danger }} />
                          </div>
                        </div>
                      </div>
                      <div style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted }}>
                        {risk.attack_count}
                      </div>
                    </div>
                  </div>

                  {isOpen && (
                    <div className="expanded-details">
                      <div style={{ display: 'flex', gap: '0', flexWrap: 'wrap', padding: '0' }}>
                        {[
                          { label: 'First Seen',   value: new Date(risk.first_seen).toLocaleString() },
                          { label: 'Last Seen',    value: new Date(risk.last_seen).toLocaleString() },
                          { label: 'Total Events', value: String(risk.attack_count) },
                          { label: 'Risk Score',   value: `${risk.risk_score.toFixed(1)} / 100` },
                        ].map((d, j) => (
                          <div key={j} style={{ flex: '1 1 180px', padding: '14px 20px', borderRight: `1px solid ${T.border}` }}>
                            <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '5px' }}>{d.label}</div>
                            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: j === 2 ? T.danger : j === 3 ? sc : T.text }}>{d.value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div style={{ padding: '40px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.muted }}>
            {error ? 'unable to load risk data' : 'no risk data available'}
          </div>
        )}
      </div>
    </div>
  )
}

export default RiskAnalysis
