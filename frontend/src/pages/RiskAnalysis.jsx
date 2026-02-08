import React, { useState } from 'react'
import { AlertCircle, ChevronDown } from 'lucide-react'
import { usePolling } from '../hooks/usePolling'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function RiskAnalysis() {
  const [expandedIP, setExpandedIP] = useState(null)
  const [window, setWindow] = useState('1h')
  const { data, error } = usePolling(`http://127.0.0.1:8000/api/analytics/risk?window=${window}`)

  const risks = data?.risks || []

  const getSeverityBadge = (score) => {
    if (score < 30) return { text: 'Low', color: '#34a853' }
    if (score < 70) return { text: 'Medium', color: '#fbbc04' }
    return { text: 'High', color: '#ea4335' }
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
          Risk Analysis
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Intelligence-driven per-IP risk assessment</p>
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
            <button
              onClick={() => setWindow('1h')}
              style={{
                padding: '6px 12px',
                background: window === '1h' ? '#1f71e5' : 'transparent',
                color: window === '1h' ? 'white' : '#5f6368',
                border: '1px solid #dadce0',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
              }}
            >
              1h
            </button>
            <button
              onClick={() => setWindow('24h')}
              style={{
                padding: '6px 12px',
                background: window === '24h' ? '#1f71e5' : 'transparent',
                color: window === '24h' ? 'white' : '#5f6368',
                border: '1px solid #dadce0',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
              }}
            >
              24h
            </button>
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
                    background:
                      risk.risk_score > 70
                        ? 'rgba(234, 67, 53, 0.05)'
                        : 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      width: '100%',
                      gap: '16px',
                      padding: '12px 16px',
                    }}
                  >
                    <ChevronDown
                      size={18}
                      style={{
                        transform: expandedIP === index ? 'rotate(180deg)' : 'rotate(0deg)',
                        transition: 'transform 0.2s',
                        color: 'var(--text-secondary)',
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ minWidth: '120px' }}>
                      <div style={{ fontFamily: 'monospace', fontSize: '13px', color: 'var(--accent-blue)' }}>
                        {risk.ip_address}
                      </div>
                    </div>
                    <div style={{ minWidth: '100px' }}>
                      <div className="risk-bar">
                        <span style={{ minWidth: '30px' }}>{risk.risk_score.toFixed(1)}</span>
                        <div className="risk-bar-container">
                          <div
                            className="risk-bar-fill"
                            style={{
                              width: `${Math.min(risk.risk_score, 100)}%`,
                              background:
                                risk.risk_score > 70
                                  ? '#ea4335'
                                  : risk.risk_score > 40
                                  ? '#fbbc04'
                                  : '#34a853',
                            }}
                          ></div>
                        </div>
                      </div>
                    </div>
                    <div style={{ minWidth: '80px' }}>
                      <span
                        style={{
                          background: getSeverityBadge(risk.risk_score).color + '20',
                          color: getSeverityBadge(risk.risk_score).color,
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: 500,
                        }}
                      >
                        {getSeverityBadge(risk.risk_score).text}
                      </span>
                    </div>
                    <div style={{ minWidth: '150px' }}>
                      {getConfidenceBar(risk.confidence)}
                    </div>
                    <div style={{ minWidth: '50px', textAlign: 'right', color: 'var(--text-secondary)' }}>
                      {risk.attack_count} attacks
                    </div>
                  </div>
                </div>

                {expandedIP === index && (
                  <div className="expanded-details">
                    <div style={{ padding: '16px', borderLeft: '3px solid #1f71e5', background: 'var(--bg-card)' }}>
                      <div style={{ marginBottom: '16px' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                          Confidence Explanation
                        </h4>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                          {risk.confidence_explanation || 'No explanation available'}
                        </p>
                      </div>

                      <div style={{ marginBottom: '16px' }}>
                        <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                          Attack Types
                        </h4>
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          {risk.attack_labels?.map((label, i) => (
                            <span
                              key={i}
                              style={{
                                background: 'var(--accent-blue-light)',
                                color: 'var(--accent-blue)',
                                padding: '4px 8px',
                                borderRadius: '3px',
                                fontSize: '11px',
                              }}
                            >
                              {label}
                            </span>
                          )) || (
                            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                              No attack labels
                            </span>
                          )}
                        </div>
                      </div>

                      {risk.timeline && risk.timeline.length > 0 && (
                        <div style={{ marginBottom: '16px' }}>
                          <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                            Activity Timeline
                          </h4>
                          <div style={{ height: '150px', width: '100%' }}>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={risk.timeline}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
                                <XAxis
                                  dataKey="time"
                                  tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                                />
                                <YAxis
                                  tick={{ fontSize: 11, fill: 'var(--text-secondary)' }}
                                />
                                <Tooltip
                                  contentStyle={{
                                    background: 'var(--bg-card)',
                                    border: '1px solid var(--border-medium)',
                                    borderRadius: '4px',
                                  }}
                                  labelStyle={{ color: 'var(--text-primary)' }}
                                />
                                <Line
                                  type="monotone"
                                  dataKey="risk_score"
                                  stroke="#1f71e5"
                                  strokeWidth={2}
                                  dot={{ r: 3 }}
                                />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      )}
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
