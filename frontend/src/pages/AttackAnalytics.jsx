import React, { useState, useEffect } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import { fetchTopAttackers } from '../api/api'

const T = {
  border: 'rgba(255,255,255,0.10)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

function sevBadge(score) {
  if (score >= 70) return { bg: 'rgba(255,255,255,0.14)', border: 'rgba(255,255,255,0.38)', color: '#fff',                    weight: 700, shadow: '0 0 8px rgba(255,255,255,0.12)' }
  if (score >= 30) return { bg: 'rgba(255,255,255,0.07)', border: 'rgba(255,255,255,0.22)', color: 'rgba(255,255,255,0.85)', weight: 600, shadow: 'none' }
  return             { bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.55)', weight: 500, shadow: 'none' }
}

function sevBarAlpha(score) {
  if (score >= 70) return { alpha: 0.95, glow: '0 0 6px rgba(255,255,255,0.4)' }
  if (score >= 30) return { alpha: 0.58, glow: 'none' }
  return             { alpha: 0.28, glow: 'none' }
}

function AttackAnalytics() {
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

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '5px' }}>
          Threat Intelligence
        </div>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '22px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
          Attack Analytics
        </div>
      </div>

      {error && <div className="demo-banner"><AlertCircle size={13} /> Backend offline — check API connection</div>}

      <div className="table-container">
        <div className="table-header">
          <div>
            <span className="chart-title" style={{ margin: 0 }}>Top attackers by threat score</span>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, marginTop: '3px' }}>click row to expand</div>
          </div>
          <div style={{ display: 'flex', gap: '4px' }}>
            {['1h', '24h'].map(w => (
              <button key={w} onClick={() => setTimeWindow(w)} className={`time-btn ${timeWindow === w ? 'active' : ''}`}>{w}</button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '9px 16px 9px 20px', borderBottom: `1px solid ${T.border}` }}>
          <div style={{ width: '16px' }} />
          {['IP Address', 'Threat Score', 'Level', 'Confidence', 'Events'].map((h, i) => (
            <div key={h} style={{ minWidth: i < 4 ? (i === 2 ? '80px' : i === 3 ? '150px' : '140px') : undefined, marginLeft: i === 4 ? 'auto' : undefined, fontFamily: "'Inter', sans-serif", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em' }}>
              {h}
            </div>
          ))}
        </div>

        {risks.length > 0 ? (
          <div className="expandable-table">
            {risks.map((risk, i) => {
              const sb  = sevBadge(risk.risk_score)
              const bar = sevBarAlpha(risk.risk_score)
              const confBar = sevBarAlpha(risk.confidence)
              const isOpen = expandedIP === i
              return (
                <div key={i} className="expandable-row-wrapper">
                  <div
                    className="expandable-row"
                    onClick={() => setExpandedIP(isOpen ? null : i)}
                    style={{ borderLeft: risk.risk_score >= 70 ? '2px solid rgba(255,255,255,0.45)' : '2px solid transparent' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '11px 16px 11px 18px' }}>
                      <ChevronDown size={13} style={{ color: T.dim, flexShrink: 0, transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
                      <div style={{ minWidth: '140px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.text, fontWeight: 600 }}>{risk.ip}</div>
                      <div style={{ minWidth: '140px' }}>
                        <div className="risk-bar">
                          <span style={{ minWidth: '36px', color: T.text, fontWeight: sb.weight, fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px' }}>{risk.risk_score.toFixed(1)}</span>
                          <div className="risk-bar-container">
                            <div className="risk-bar-fill" style={{ width: `${Math.min(risk.risk_score, 100)}%`, background: `rgba(255,255,255,${bar.alpha})`, boxShadow: bar.glow }} />
                          </div>
                        </div>
                      </div>
                      <div style={{ minWidth: '80px' }}>
                        <span style={{ background: sb.bg, color: sb.color, border: `1px solid ${sb.border}`, padding: '3px 9px', borderRadius: '6px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: sb.weight, textTransform: 'uppercase', letterSpacing: '0.04em', boxShadow: sb.shadow }}>
                          {risk.severity}
                        </span>
                      </div>
                      <div style={{ minWidth: '150px' }}>
                        <div className="risk-bar">
                          <span style={{ minWidth: '36px', color: T.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px' }}>{risk.confidence.toFixed(0)}%</span>
                          <div className="risk-bar-container">
                            <div className="risk-bar-fill" style={{ width: `${Math.min(risk.confidence, 100)}%`, background: `rgba(255,255,255,${confBar.alpha})` }} />
                          </div>
                        </div>
                      </div>
                      <div style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted, fontWeight: risk.attack_count > 50 ? 700 : 400 }}>
                        {risk.attack_count}
                      </div>
                    </div>
                  </div>

                  {isOpen && (
                    <div className="expanded-details">
                      <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                        {[
                          { label: 'First Seen',    value: new Date(risk.first_seen).toLocaleString() },
                          { label: 'Last Seen',     value: new Date(risk.last_seen).toLocaleString() },
                          { label: 'Total Events',  value: String(risk.attack_count), bold: true },
                          { label: 'Threat Score',  value: `${risk.risk_score.toFixed(1)} / 100`, bold: risk.risk_score >= 70 },
                        ].map((d, j) => (
                          <div key={j} style={{ flex: '1 1 180px', padding: '14px 20px', borderRight: `1px solid ${T.border}` }}>
                            <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '5px' }}>{d.label}</div>
                            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.text, fontWeight: d.bold ? 700 : 400 }}>{d.value}</div>
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
          <div style={{ padding: '48px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.dim }}>
            {error ? 'unable to load analytics' : 'no threat data available'}
          </div>
        )}
      </div>
    </div>
  )
}

export default AttackAnalytics
