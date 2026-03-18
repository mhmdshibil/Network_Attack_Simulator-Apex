import React, { useState, useEffect } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import { fetchTopAttackers } from '../api/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function RiskAnalysis() {
  const [expandedIP, setExpandedIP] = useState(null)
  const [timeWindow, setTimeWindow] = useState('24h')
  const [risks, setRisks] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchTopAttackers()
        const attackers = result?.attackers || []

        // Build risk scores from attacker data
        const computed = attackers.map(attacker => {
          const maxCount = 200
          const riskScore = Math.min((attacker.count / maxCount) * 100, 100)
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
      } catch (err) {
        setError(err.message)
      }
    }

    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [timeWindow])

  const getSeverityBadge = (score) => {
    if (score < 30) return { text: 'Low', color: '#34a853' }
    if (score < 70) return { text: 'Medium', color: '#fbbc04' }
    return { text: 'High', color: '#ea4335' }
  }

  const getConfidenceBar = (confidence) => (
    <div className="risk-bar">
      <span style={{ minWidth: '36px', fontSize: '12px' }}>{confidence.toFixed(1)}%</span>
      <div className="risk-bar-container">
        <div
          className="risk-bar-fill"
          style={{
            width: `${Math.min(confidence, 100)}%`,
            background: confidence > 70 ? '#34a853' : confidence > 40 ? '#fbbc04' : '#ea4335',
          }}
        />
      </div>
    </div>
  )

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '32px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Risk Analysis
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Intelligence-driven per-IP risk assessment
        </p>
      </div>

      {error && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline - Check your API connection
        </div>
      )}

      <div className="table-container">
        <div className="table-header">
          <div>
            <h3 className="chart-title">Risk Scores by IP</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Click row to expand details
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {['1h', '24h'].map(w => (
              <button
                key={w}
                onClick={() => setTimeWindow(w)}
                style={{
                  padding: '6px 12px',
                  background: timeWindow === w ? '#1f71e5' : 'transparent',
                  color: timeWindow === w ? 'white' : '#5f6368',
                  border: '1px solid #dadce0',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px',
                }}
              >
                {w}
              </button>
            ))}
          </div>
        </div>

        {risks.length > 0 ? (
          <div className="expandable-table">
            {risks.map((risk, index) => (
              <div key={index} className="expandable-row-wrapper">
                <div
                  className="expandable-row"
                  onClick={() => setExpandedIP(expandedIP === index ? null : index)}
                  style={{
                    background: risk.risk_score > 70 ? 'rgba(234, 67, 53, 0.05)' : 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    width: '100%',
                    gap: '16px',
                    padding: '12px 16px',
                  }}>
                    <ChevronDown
                      size={18}
                      style={{
                        transform: expandedIP === index ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s',
                        color: 'var(--text-secondary)',
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ minWidth: '130px' }}>
                      <div style={{ fontFamily: 'monospace', fontSize: '13px', color: 'var(--accent-blue)' }}>
                        {risk.ip}
                      </div>
                    </div>
                    <div style={{ minWidth: '130px' }}>
                      <div className="risk-bar">
                        <span style={{ minWidth: '36px', fontSize: '12px' }}>{risk.risk_score.toFixed(1)}</span>
                        <div className="risk-bar-container">
                          <div
                            className="risk-bar-fill"
                            style={{
                              width: `${Math.min(risk.risk_score, 100)}%`,
                              background: risk.risk_score > 70 ? '#ea4335' : risk.risk_score > 40 ? '#fbbc04' : '#34a853',
                            }}
                          />
                        </div>
                      </div>
                    </div>
                    <div style={{ minWidth: '80px' }}>
                      <span style={{
                        background: getSeverityBadge(risk.risk_score).color + '20',
                        color: getSeverityBadge(risk.risk_score).color,
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 500,
                      }}>
                        {getSeverityBadge(risk.risk_score).text}
                      </span>
                    </div>
                    <div style={{ minWidth: '160px' }}>
                      {getConfidenceBar(risk.confidence)}
                    </div>
                    <div style={{ minWidth: '80px', textAlign: 'right', color: 'var(--text-secondary)', fontSize: '13px' }}>
                      {risk.attack_count} attacks
                    </div>
                  </div>
                </div>

                {expandedIP === index && (
                  <div className="expanded-details">
                    <div style={{ padding: '16px', borderLeft: '3px solid #1f71e5', background: 'var(--bg-card)' }}>
                      <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap', marginBottom: '12px' }}>
                        <div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>FIRST SEEN</div>
                          <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                            {new Date(risk.first_seen).toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>LAST SEEN</div>
                          <div style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                            {new Date(risk.last_seen).toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>TOTAL ATTACKS</div>
                          <div style={{ fontSize: '13px', color: '#ea4335', fontWeight: 600 }}>
                            {risk.attack_count}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>RISK SCORE</div>
                          <div style={{ fontSize: '13px', color: getSeverityBadge(risk.risk_score).color, fontWeight: 600 }}>
                            {risk.risk_score.toFixed(1)} / 100
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
            {error ? 'Unable to load risk data' : 'No risk data available'}
          </p>
        )}
      </div>
    </div>
  )
}

export default RiskAnalysis