import React, { useState, useEffect } from 'react'
import { fetchExplainSummary } from '../api/api'
import './ModelInsights.css'

const FEATURE_LABELS = {
  packets_per_second: 'Packets / Second',
  avg_request_rate: 'Avg Request Rate',
  failed_connections: 'Failed Connections',
  unique_ports: 'Unique Ports',
  bytes_per_packet: 'Bytes / Packet',
  connection_duration: 'Connection Duration',
  payload_entropy: 'Payload Entropy',
}

const CLASS_COLORS = {
  normal: '#6e8',
  port_scan: '#f80',
  ddos: '#e33',
  bruteforce: '#e93',
  sql_injection: '#c6f',
  malware: '#f66',
  unknown_anomaly: '#6af',
}

function Bar({ value, maxValue, color }) {
  const pct = maxValue > 0 ? Math.round((value / maxValue) * 100) : 0
  return (
    <div className="mi-bar-track">
      <div
        className="mi-bar-fill"
        style={{ width: `${pct}%`, background: color || 'rgba(130,180,255,0.7)' }}
      />
    </div>
  )
}

function ModelInsights() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = async () => {
      try {
        const d = await fetchExplainSummary()
        if (!d) throw new Error('No data returned')
        setData(d)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
    const iv = setInterval(load, 30000)
    return () => clearInterval(iv)
  }, [])

  const T = {
    bg: '#0a0a0a',
    card: '#0d0d0d',
    border: 'rgba(255,255,255,0.08)',
    text: '#fff',
    muted: 'rgba(255,255,255,0.45)',
    accent: 'rgba(130,180,255,0.7)',
    font: "'IBM Plex Mono',monospace",
    sans: "'Space Grotesk',sans-serif",
  }

  const section = (title, children) => (
    <div style={{
      background: T.card,
      border: `1px solid ${T.border}`,
      borderRadius: '14px',
      padding: '24px 28px',
      marginBottom: '20px',
    }}>
      <div style={{
        fontSize: '10px', fontWeight: 700, color: T.muted,
        letterSpacing: '0.14em', textTransform: 'uppercase',
        marginBottom: '20px', fontFamily: T.font,
      }}>
        {title}
      </div>
      {children}
    </div>
  )

  if (loading) {
    return (
      <div style={{ padding: '32px', color: T.muted, fontFamily: T.font, fontSize: '12px' }}>
        Loading model insights…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div style={{ padding: '32px', color: 'rgba(220,50,50,0.8)', fontFamily: T.font, fontSize: '12px' }}>
        {error || 'Unable to load model insights.'}
      </div>
    )
  }

  const maxImportance = Math.max(...data.feature_importance.map(f => f.importance), 0.001)
  const maxShap = Math.max(...data.feature_importance.map(f => f.mean_shap || 0), 0.001)

  return (
    <div style={{ padding: '28px 32px', color: T.text, fontFamily: T.font, maxWidth: '900px' }}>
      {/* Header */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontFamily: T.sans, fontSize: '26px', fontWeight: 800, margin: 0, letterSpacing: '-0.03em' }}>
          Model Insights
        </h1>
        <div style={{ fontSize: '11px', color: T.muted, marginTop: '6px', letterSpacing: '0.04em' }}>
          Random Forest v2 · 7 features · {data.total_explanations} live SHAP explanations
        </div>
      </div>

      {/* Feature Importance */}
      {section('Feature Importance (Gini + Mean SHAP)', (
        <div>
          {data.feature_importance.map((item, i) => (
            <div key={item.feature} style={{ marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '5px', gap: '8px' }}>
                <span className="mi-rank">#{item.rank}</span>
                <span style={{ fontSize: '12px', color: T.text, flex: 1 }}>
                  {FEATURE_LABELS[item.feature] || item.feature}
                </span>
                <span style={{ fontSize: '11px', color: T.muted, minWidth: '48px', textAlign: 'right' }}>
                  {(item.importance * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '9px', color: T.muted, width: '32px', textAlign: 'right', letterSpacing: '0.06em' }}>GINI</span>
                  <Bar value={item.importance} maxValue={maxImportance} color="rgba(130,180,255,0.7)" />
                </div>
                {item.mean_shap > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '9px', color: T.muted, width: '32px', textAlign: 'right', letterSpacing: '0.06em' }}>SHAP</span>
                    <Bar value={item.mean_shap} maxValue={maxShap} color="rgba(180,130,255,0.6)" />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}

      {/* Per-class top features */}
      {Object.keys(data.per_class_top_features).length > 0 && section('Top SHAP Features by Attack Class', (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
          {Object.entries(data.per_class_top_features).map(([cls, feats]) => (
            <div key={cls} style={{
              background: 'rgba(255,255,255,0.03)',
              border: `1px solid ${T.border}`,
              borderRadius: '10px',
              padding: '14px 16px',
            }}>
              <div style={{
                fontSize: '10px', fontWeight: 700,
                color: CLASS_COLORS[cls] || T.muted,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                marginBottom: '8px',
              }}>
                {cls.replace(/_/g, ' ')}
              </div>
              {feats.map((f, i) => (
                <div key={f} style={{
                  fontSize: '11px',
                  color: i === 0 ? T.text : T.muted,
                  marginBottom: '3px',
                  paddingLeft: '8px',
                  borderLeft: `2px solid ${i === 0 ? (CLASS_COLORS[cls] || T.accent) : 'transparent'}`,
                }}>
                  {FEATURE_LABELS[f] || f}
                </div>
              ))}
            </div>
          ))}
        </div>
      ))}

      {/* Meta */}
      <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.2)', marginTop: '8px', letterSpacing: '0.04em' }}>
        Model version: {data.model_version} · Features: {(data.feature_columns || []).join(', ')}
      </div>
    </div>
  )
}

export default ModelInsights
