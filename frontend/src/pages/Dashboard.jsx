import React, { useRef, useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertCircle, Shield, AlertTriangle, Activity, Eye, Globe } from 'lucide-react'
import { useCursorPhysics } from '../hooks/useCursorPhysics'
import { useCountUp } from '../hooks/useCountUp'
import { fetchHealth, fetchMetrics, fetchTimeline, fetchAlerts } from '../api/api'

/* Monochrome tokens */
const T = {
  bg:          '#000000',
  panel:       '#0a0a0a',
  border:      'rgba(255,255,255,0.10)',
  borderMid:   'rgba(255,255,255,0.18)',
  text:        '#ffffff',
  muted:       'rgba(255,255,255,0.55)',
  dim:         'rgba(255,255,255,0.28)',
  /* Chart lines — white at two intensities, no hue */
  lineA:       'rgba(255,255,255,0.80)',
  lineB:       'rgba(255,255,255,0.40)',
}

/* Gradient-border panel */
const panelStyle = {
  background: `linear-gradient(${T.panel}, ${T.panel}) padding-box, linear-gradient(135deg, rgba(255,255,255,0.13) 0%, rgba(255,255,255,0.04) 100%) border-box`,
  border: '1px solid transparent',
  borderRadius: '18px',
  boxShadow: '0 0 0 1px rgba(255,255,255,0.05), 0 2px 16px rgba(0,0,0,0.8)',
}

/* ── Tooltip ─────────────────────────────────────────────────── */
const SOCTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ ...panelStyle, padding: '10px 14px', fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', color: T.text }}>
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

/* ── Stat block ──────────────────────────────────────────────── */
const StatBlock = ({ label, value }) => (
  <div style={{ flex: '1 1 110px', padding: '16px 18px', borderRight: `1px solid ${T.border}` }}>
    <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em', marginBottom: '6px' }}>{label}</div>
    <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: '22px', fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>{value}</div>
  </div>
)

/* ── Pipeline step ───────────────────────────────────────────── */
const PipeStep = ({ n, title, desc }) => (
  <div style={{ flex: '1 1 140px', padding: '16px', borderRight: `1px solid ${T.border}` }}>
    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '18px', fontWeight: 600, color: T.dim, marginBottom: '4px' }}>{n}</div>
    <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '10px', fontWeight: 700, color: T.text, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{title}</div>
    <p style={{ fontSize: '11px', color: T.muted, lineHeight: '1.6', margin: 0, maxWidth: 'none' }}>{desc}</p>
  </div>
)

/* ── Spec row ────────────────────────────────────────────────── */
const SpecRow = ({ label, value }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: `1px solid ${T.border}` }}>
    <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '12px', color: T.muted }}>{label}</span>
    <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px', color: T.text, background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '6px' }}>{value}</span>
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
      } catch { }
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
    { label: 'System Health',    value: healthData?.status === 'ok' ? 'OK' : healthData?.status ?? '—', subtext: 'API connection', icon: Shield,        cls: 'health' },
    { label: 'Total Detections', value: countDetections ?? '—',                                          subtext: 'all time',       icon: AlertTriangle, cls: 'detections' },
    { label: 'Active Risky IPs', value: countRiskyIPs   ?? '—',                                          subtext: 'monitored',      icon: Globe,         cls: 'risky' },
    { label: 'Monitor Actions',  value: countMonitor     ?? '—',                                          subtext: metricsData?.last_detection ? new Date(metricsData.last_detection).toLocaleTimeString() : 'no events', icon: Eye, cls: 'confidence' },
  ]

  return (
    <div>
      {isOffline && (
        <div className="demo-banner">
          <AlertCircle size={13} /> Backend offline — check API connection
        </div>
      )}

      {/* Metric cards */}
      <div className="metrics-grid" style={{ marginBottom: '20px' }}>
        {cards.map((card, i) => {
          const Icon = card.icon
          return (
            <div key={i} ref={el => cardRefs.current[i] = el} className={`metric-card ${card.cls}`} style={{ willChange: 'transform' }}>
              <div className="metric-label">
                <Icon size={11} style={{ opacity: 0.55 }} />
                {card.label}
              </div>
              <div className="metric-value">{card.value}</div>
              <div className="metric-subtext">{card.subtext}</div>
            </div>
          )
        })}
      </div>

      {/* Traffic timeline */}
      {timelineData.length > 0 && (
        <div className="chart-container" style={{ marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Activity size={12} style={{ color: T.muted }} />
            <span className="chart-title" style={{ margin: 0 }}>Traffic Timeline</span>
            <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, letterSpacing: '0.06em', border: `1px solid ${T.border}`, padding: '2px 7px', borderRadius: '6px' }}>LIVE · 24H</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={timelineData} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="gPkts" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#fff" className="breathe-stop" />
                  <stop offset="95%" stopColor="#fff" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gEvts" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#fff" stopOpacity={0.12}/>
                  <stop offset="95%" stopColor="#fff" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: T.muted, fontFamily: "'IBM Plex Mono'" }} axisLine={{ stroke: T.border }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} width={32} />
              <Tooltip content={<SOCTooltip />} />
              <Area type="monotone" dataKey="packets" stroke={T.lineA} strokeWidth={1.5} fill="url(#gPkts)" dot={false} name="Packets" />
              <Area type="monotone" dataKey="events"  stroke={T.lineB} strokeWidth={1}   fill="url(#gEvts)" dot={false} name="Events" />
            </AreaChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: '20px', marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${T.border}` }}>
            {[{ c: T.lineA, l: 'Packets' }, { c: T.lineB, l: 'Events' }].map((x, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: "'IBM Plex Mono'", fontSize: '10px', color: T.muted }}>
                <div style={{ width: '18px', height: '2px', background: x.c }} />
                {x.l}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Live Alerts */}
      <div className="chart-container" style={{ padding: 0, marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '14px 22px', borderBottom: `1px solid ${T.border}` }}>
          <AlertTriangle size={12} style={{ color: T.muted }} />
          <span className="chart-title" style={{ margin: 0 }}>Live Alerts</span>
          <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, letterSpacing: '0.06em' }}>LAST 20</span>
        </div>
        {alertsData.length === 0 ? (
          <div style={{ padding: '32px 22px', textAlign: 'center', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.dim }}>
            awaiting detections…
          </div>
        ) : (
          <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
            {alertsData.map(alert => {
              /* Severity via dot size + text weight, no hue */
              const isHigh = alert.severity === 'high'
              return (
                <div
                  key={`${alert.ip}-${alert.timestamp}`}
                  className={`alert-row alert-row-${alert.severity}`}
                >
                  <span style={{
                    width: isHigh ? '6px' : '5px',
                    height: isHigh ? '6px' : '5px',
                    borderRadius: '50%',
                    flexShrink: 0,
                    background: isHigh ? 'rgba(255,255,255,0.90)' : 'rgba(255,255,255,0.45)',
                    boxShadow: isHigh ? '0 0 5px rgba(255,255,255,0.5)' : 'none',
                  }} />
                  <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, flex: 1, fontWeight: isHigh ? 600 : 400 }}>
                    {alert.message}
                  </span>
                  <span style={{
                    fontFamily: "'IBM Plex Mono',monospace",
                    fontSize: '9px',
                    letterSpacing: '0.06em',
                    color: isHigh ? '#fff' : T.muted,
                    background: isHigh ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.05)',
                    border: `1px solid ${isHigh ? 'rgba(255,255,255,0.30)' : 'rgba(255,255,255,0.12)'}`,
                    padding: '2px 7px',
                    borderRadius: '6px',
                    flexShrink: 0,
                    fontWeight: isHigh ? 700 : 500,
                  }}>
                    {alert.action}
                  </span>
                  <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, flexShrink: 0, minWidth: '54px', textAlign: 'right' }}>
                    {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* System Overview */}
      <div style={{ ...panelStyle, marginTop: '8px' }}>

        <div style={{ padding: '14px 22px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '10px', fontWeight: 700, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em' }}>System Overview</span>
          <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.muted, border: `1px solid ${T.border}`, padding: '2px 7px', borderRadius: '6px' }}>v1.0 · LIVE</span>
        </div>

        <div style={{ padding: '20px 22px', borderBottom: `1px solid ${T.border}` }}>
          <p style={{ fontSize: '13px', color: T.text, lineHeight: '1.7', marginBottom: '6px', maxWidth: 'none', fontWeight: 500, fontFamily: "'Inter', sans-serif" }}>
            <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, letterSpacing: '-0.01em' }}>Apex-Kinetics</span> — autonomous real-time network threat intelligence and response platform.
          </p>
          <p style={{ fontSize: '13px', color: T.muted, lineHeight: '1.7', margin: 0, maxWidth: 'none', fontFamily: "'Inter', sans-serif" }}>
            Detects, classifies, and neutralises malicious network activity across 5 attack vectors with zero human intervention required. Every packet is a data point. Every anomaly triggers a logged decision.
          </p>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', borderBottom: `1px solid ${T.border}` }}>
          {[
            { label: 'Attack Vectors', value: '5' },
            { label: 'Response Time',  value: '<1s' },
            { label: 'Decision Types', value: '3' },
            { label: 'API Endpoints',  value: '15+' },
            { label: 'Data Retention', value: '30d' },
            { label: 'Uptime Target',  value: '99.9%' },
          ].map((s, i) => <StatBlock key={i} label={s.label} value={s.value} />)}
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
            <div key={i} style={{ padding: '16px 20px', borderRight: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 700, color: T.text, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '7px' }}>{c.label}</div>
              <p style={{ fontSize: '11px', color: T.muted, lineHeight: '1.65', margin: 0, maxWidth: 'none' }}>{c.desc}</p>
            </div>
          ))}
        </div>

        <div style={{ borderBottom: `1px solid ${T.border}` }}>
          <div style={{ padding: '10px 22px', borderBottom: `1px solid ${T.border}`, fontFamily: "'Inter', sans-serif", fontSize: '10px', fontWeight: 700, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.10em' }}>
            Detection Pipeline
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap' }}>
            <PipeStep n="01" title="Ingest"    desc="Raw network packets captured and written to the detection pipeline in real time." />
            <PipeStep n="02" title="Classify"  desc="ML engine labels each event: DDoS, brute-force, port-scan, SQL injection, or malware." />
            <PipeStep n="03" title="Correlate" desc="Events grouped by IP and time window; coordinated campaigns identified and flagged." />
            <PipeStep n="04" title="Score"     desc="Each IP gets a 0–100 risk score with confidence level and HIGH / MEDIUM / LOW severity." />
            <PipeStep n="05" title="Respond"   desc="Automated BLOCK / RATE-LIMIT / MONITOR executed instantly and written to the audit log." />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
          <div style={{ padding: '18px 22px', borderRight: `1px solid ${T.border}` }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>Backend</div>
            <SpecRow label="Python"  value="≥ 3.10" />
            <SpecRow label="FastAPI" value="≥ 0.100" />
            <SpecRow label="Pandas"  value="≥ 2.0" />
            <SpecRow label="RAM"     value="≥ 512 MB" />
          </div>
          <div style={{ padding: '18px 22px' }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '12px' }}>Frontend</div>
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
