import React, { useRef, useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertCircle, Shield, AlertTriangle, Activity, Eye, Globe } from 'lucide-react'
import { useCursorPhysics } from '../hooks/useCursorPhysics'
import { useCountUp } from '../hooks/useCountUp'
import { fetchHealth, fetchMetrics, fetchTimeline, fetchAlerts } from '../api/api'

const T = {
  bg:      '#131316',
  border:  '#232328',
  text:    '#F2F3F5',
  muted:   '#6E7180',
  accent:  '#2DD9FF',
  danger:  '#FF3B5C',
  warning: '#FFA63D',
}

/* ── Shared tooltip ──────────────────────────────────────────── */
const SOCTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: T.bg, border: `1px solid ${T.border}`,
      borderRadius: '2px', padding: '10px 14px',
      fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', color: T.text,
    }}>
      <div style={{ color: T.muted, marginBottom: '6px', letterSpacing: '0.05em' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, display: 'flex', justifyContent: 'space-between', gap: '20px', marginTop: '3px' }}>
          <span style={{ opacity: 0.6 }}>{p.name}</span>
          <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

/* ── Label + value stat block ────────────────────────────────── */
const StatBlock = ({ label, value, accent = T.muted }) => (
  <div style={{ flex: '1 1 100px', padding: '16px 18px', borderRight: `1px solid ${T.border}` }}>
    <div style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '6px' }}>{label}</div>
    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '22px', fontWeight: 600, color: accent, letterSpacing: '-0.01em' }}>{value}</div>
  </div>
)

/* ── Pipeline step ───────────────────────────────────────────── */
const PipeStep = ({ n, title, desc, accent }) => (
  <div style={{ flex: '1 1 140px', padding: '16px', borderRight: `1px solid ${T.border}` }}>
    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '18px', fontWeight: 600, color: T.border, marginBottom: '4px' }}>{n}</div>
    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', fontWeight: 600, color: accent, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{title}</div>
    <p style={{ fontSize: '11px', color: T.muted, lineHeight: '1.6', margin: 0, maxWidth: 'none' }}>{desc}</p>
  </div>
)

/* ── Spec row ────────────────────────────────────────────────── */
const SpecRow = ({ label, value }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: `1px solid ${T.border}` }}>
    <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: '12px', color: T.muted }}>{label}</span>
    <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', color: T.text, background: T.border, padding: '2px 8px', borderRadius: '2px' }}>{value}</span>
  </div>
)

function Dashboard() {
  const [healthData, setHealthData]     = useState(null)
  const [metricsData, setMetricsData]   = useState(null)
  const [timelineData, setTimelineData] = useState([])
  const [alertsData, setAlertsData]     = useState([])
  const [isOffline, setIsOffline]       = useState(false)
  const cardRefs = useRef([])
  const { getInfluence } = useCursorPhysics()

  /* ── Count-up for numeric stat cards ── */
  const countDetections = useCountUp(typeof metricsData?.total_detections === 'number' ? metricsData.total_detections : null)
  const countRiskyIPs   = useCountUp(typeof metricsData?.unique_blocked_ips === 'number' ? metricsData.unique_blocked_ips : null)
  const countMonitor    = useCountUp(typeof metricsData?.monitor_actions === 'number' ? metricsData.monitor_actions : null)

  useEffect(() => {
    const load = async () => {
      try {
        const [health, metrics, timeline] = await Promise.all([fetchHealth(), fetchMetrics(), fetchTimeline('24h')])
        if (!health || !metrics || !timeline) { setIsOffline(true); return }
        setHealthData(health)
        setMetricsData(metrics)
        setTimelineData((timeline.timeline || []).map(item => ({
          timestamp: new Date(item.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          packets: item.packets,
          events: item.events,
        })))
        setIsOffline(false)
      } catch { setIsOffline(true) }
    }
    load()
    const iv = setInterval(load, 5000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    const loadAlerts = async () => {
      try {
        const data = await fetchAlerts(20)
        if (Array.isArray(data)) setAlertsData(data)
      } catch { /* pass */ }
    }
    loadAlerts()
    const iv = setInterval(loadAlerts, 5000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    let frameId
    const applyPhysics = () => {
      cardRefs.current.forEach(ref => {
        if (!ref) return
        const rect = ref.getBoundingClientRect()
        const influence = getInfluence(rect, 200, 6)
        ref.style.transform = `translate(${influence.x}px, ${influence.y}px)`
      })
      frameId = requestAnimationFrame(applyPhysics)
    }
    frameId = requestAnimationFrame(applyPhysics)
    return () => cancelAnimationFrame(frameId)
  }, [getInfluence])

  const cards = [
    { label: 'System Health',    value: healthData?.status === 'ok' ? 'OK' : healthData?.status ?? '—', subtext: 'API connection', icon: Shield,        accent: T.accent,  cls: 'health' },
    { label: 'Total Detections', value: countDetections ?? '—',                                          subtext: 'all time',       icon: AlertTriangle, accent: T.warning, cls: 'detections' },
    { label: 'Active Risky IPs', value: countRiskyIPs   ?? '—',                                          subtext: 'monitored',      icon: Globe,         accent: T.danger,  cls: 'risky' },
    { label: 'Monitor Actions',  value: countMonitor     ?? '—',                                          subtext: metricsData?.last_detection ? new Date(metricsData.last_detection).toLocaleTimeString() : 'no events', icon: Eye, accent: '#4A7FD4', cls: 'confidence' },
  ]

  return (
    <div>
      {isOffline && (
        <div className="demo-banner">
          <AlertCircle size={13} /> Backend offline — check API connection
        </div>
      )}

      {/* ── Metric cards ── */}
      <div className="metrics-grid" style={{ marginBottom: '20px' }}>
        {cards.map((card, i) => {
          const Icon = card.icon
          return (
            <div key={i} ref={el => cardRefs.current[i] = el} className={`metric-card ${card.cls}`} style={{ willChange: 'transform' }}>
              <div className="metric-label">
                <Icon size={11} style={{ color: card.accent }} />
                {card.label}
              </div>
              <div className="metric-value" style={{ color: card.accent }}>{card.value}</div>
              <div className="metric-subtext">{card.subtext}</div>
            </div>
          )
        })}
      </div>

      {/* ── Traffic timeline — monotone curve + ambient breathing fill ── */}
      {timelineData.length > 0 && (
        <div className="chart-container" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Activity size={12} style={{ color: T.muted }} />
            <span className="chart-title" style={{ margin: 0 }}>Traffic Timeline</span>
            <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.accent, letterSpacing: '0.06em' }}>LIVE · 24H</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={timelineData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="gPkts" x1="0" y1="0" x2="0" y2="1">
                  {/* breathe-stop drives the slow ambient opacity animation via CSS */}
                  <stop offset="5%"  stopColor={T.accent} className="breathe-stop" />
                  <stop offset="95%" stopColor={T.accent} stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gEvts" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={T.danger} stopOpacity={0.14}/>
                  <stop offset="95%" stopColor={T.danger} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: T.muted, fontFamily: "'IBM Plex Mono'" }} axisLine={{ stroke: T.border }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} width={32} />
              <Tooltip content={<SOCTooltip />} />
              <Area type="monotone" dataKey="packets" stroke={T.accent} strokeWidth={1.5} fill="url(#gPkts)" dot={false} name="Packets" />
              <Area type="monotone" dataKey="events"  stroke={T.danger} strokeWidth={1}   fill="url(#gEvts)" dot={false} name="Events" />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: '20px', marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${T.border}` }}>
            {[{ c: T.accent, l: 'Packets' }, { c: T.danger, l: 'Events' }].map((x, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: "'IBM Plex Mono'", fontSize: '10px', color: T.muted, letterSpacing: '0.05em' }}>
                <div style={{ width: '18px', height: '2px', background: x.c }} />
                {x.l}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Live Alerts — slide+fade from top, left-border severity flash ── */}
      <div className="chart-container" style={{ padding: 0, marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 20px', borderBottom: `1px solid ${T.border}` }}>
          <AlertTriangle size={12} style={{ color: T.danger }} />
          <span className="chart-title" style={{ margin: 0 }}>Live Alerts</span>
          <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.danger, letterSpacing: '0.06em' }}>LAST 20</span>
        </div>
        {alertsData.length === 0 ? (
          <div style={{ padding: '28px 20px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.muted }}>
            awaiting detections...
          </div>
        ) : (
          <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {alertsData.map(alert => (
              <div
                key={`${alert.ip}-${alert.timestamp}`}
                className={`alert-row alert-row-${alert.severity}`}
              >
                <span style={{
                  width: '5px', height: '5px', borderRadius: '50%', flexShrink: 0,
                  background: alert.severity === 'high' ? T.danger : T.warning,
                }} />
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, flex: 1 }}>
                  {alert.message}
                </span>
                <span style={{
                  fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', letterSpacing: '0.06em',
                  color:      alert.severity === 'high' ? T.danger  : T.warning,
                  background: alert.severity === 'high' ? 'rgba(255,59,92,0.1)' : 'rgba(255,166,61,0.1)',
                  border:     `1px solid ${alert.severity === 'high' ? 'rgba(255,59,92,0.25)' : 'rgba(255,166,61,0.25)'}`,
                  padding: '2px 6px', borderRadius: '2px', flexShrink: 0,
                }}>
                  {alert.action}
                </span>
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, flexShrink: 0, minWidth: '54px', textAlign: 'right' }}>
                  {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── System Overview ── */}
      <div style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: '2px', marginTop: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.4)' }}>

        <div style={{ padding: '12px 20px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>System Overview</span>
          <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.accent, border: `1px solid rgba(45,217,255,0.2)`, padding: '1px 6px', borderRadius: '2px' }}>v1.0 · LIVE</span>
        </div>

        <div style={{ padding: '18px 20px', borderBottom: `1px solid ${T.border}` }}>
          <p style={{ fontSize: '12px', color: T.text, lineHeight: '1.7', marginBottom: '6px', maxWidth: 'none', fontWeight: 500 }}>
            <span style={{ color: T.accent, fontFamily: "'IBM Plex Mono',monospace", fontWeight: 600 }}>Apex-Kinetics</span> — autonomous real-time network threat intelligence and response platform.
          </p>
          <p style={{ fontSize: '12px', color: T.muted, lineHeight: '1.7', margin: 0, maxWidth: 'none' }}>
            Detects, classifies, and neutralises malicious network activity across 5 attack vectors with zero human intervention required. Every packet is a data point. Every anomaly triggers a logged decision.
          </p>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', borderBottom: `1px solid ${T.border}` }}>
          {[
            { label: 'Attack Vectors', value: '5',     accent: T.accent },
            { label: 'Response Time',  value: '<1s',   accent: T.accent },
            { label: 'Decision Types', value: '3',     accent: T.warning },
            { label: 'API Endpoints',  value: '15+',   accent: '#4A7FD4' },
            { label: 'Data Retention', value: '30d',   accent: T.muted },
            { label: 'Uptime Target',  value: '99.9%', accent: T.muted },
          ].map((s, i) => (
            <StatBlock key={i} label={s.label} value={s.value} accent={s.accent} />
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', borderBottom: `1px solid ${T.border}` }}>
          {[
            { label: 'Detection Engine',    desc: 'ML-powered multi-vector classification. Processes live packet streams and flags anomalies with sub-second latency.' },
            { label: 'Autonomous Response', desc: 'BLOCK / RATE-LIMIT / MONITOR enforced instantly, no human approval. Thresholds adapt as cumulative threat score climbs.' },
            { label: 'IP Threat Scoring',   desc: 'Per-IP risk scores 0–100 with confidence metrics, severity tags, and full first/last-seen audit trail.' },
            { label: 'Correlation Engine',  desc: 'Cross-IP attack pattern correlation detects coordinated campaigns beyond isolated events.' },
            { label: 'Audit & Forensics',   desc: 'Every detection and response written to an immutable audit log for compliance and forensic review.' },
            { label: 'Live Analytics',      desc: '24/7 traffic timeline replay across configurable windows: 5 min → 30 days.' },
          ].map((c, i) => (
            <div key={i} style={{ padding: '14px 18px', borderRight: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.accent, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>{c.label}</div>
              <p style={{ fontSize: '11px', color: T.muted, lineHeight: '1.65', margin: 0, maxWidth: 'none' }}>{c.desc}</p>
            </div>
          ))}
        </div>

        <div style={{ borderBottom: `1px solid ${T.border}` }}>
          <div style={{ padding: '10px 20px', borderBottom: `1px solid ${T.border}`, fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            Detection Pipeline
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap' }}>
            <PipeStep n="01" title="Ingest"    desc="Raw network packets captured and written to the detection pipeline in real time."              accent="#4A7FD4" />
            <PipeStep n="02" title="Classify"  desc="ML engine labels each event: DDoS, brute-force, port-scan, SQL injection, or malware."         accent={T.warning} />
            <PipeStep n="03" title="Correlate" desc="Events grouped by IP and time window; coordinated campaigns identified and flagged."            accent="#9B59B6" />
            <PipeStep n="04" title="Score"     desc="Each IP gets a 0–100 risk score with confidence level and HIGH / MEDIUM / LOW severity."        accent={T.danger} />
            <PipeStep n="05" title="Respond"   desc="Automated BLOCK / RATE-LIMIT / MONITOR executed instantly and written to the audit log."        accent={T.accent} />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
          <div style={{ padding: '16px 20px', borderRight: `1px solid ${T.border}` }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>Backend</div>
            <SpecRow label="Python"  value="≥ 3.10" />
            <SpecRow label="FastAPI" value="≥ 0.100" />
            <SpecRow label="Pandas"  value="≥ 2.0" />
            <SpecRow label="RAM"     value="≥ 512 MB" />
          </div>
          <div style={{ padding: '16px 20px' }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '10px' }}>Frontend</div>
            <SpecRow label="Node.js" value="≥ 18.x" />
            <SpecRow label="React"   value="≥ 18" />
            <SpecRow label="Vite"    value="≥ 5" />
            <SpecRow label="Screen"  value="≥ 1280px" />
          </div>
        </div>

      </div>
    </div>
  )
}

export default Dashboard
