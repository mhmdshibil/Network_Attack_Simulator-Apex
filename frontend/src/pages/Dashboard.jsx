import React, { useRef, useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import {
  AlertCircle, Shield, AlertTriangle, Info, Cpu, Eye, Globe,
  Lock, Activity, Terminal, CheckCircle,
  Database, Network, AlertOctagon, BookOpen, Settings
} from 'lucide-react'
import { useCursorPhysics } from '../hooks/useCursorPhysics'
import { fetchHealth, fetchMetrics, fetchTimeline } from '../api/api'

const CyberTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'rgba(0,0,0,0.92)', border: '1px solid #4285f4',
      borderRadius: '6px', padding: '10px 14px', fontSize: '12px',
      color: '#e8eaed', boxShadow: '0 0 20px rgba(66,133,244,0.35)',
    }}>
      <div style={{ color: '#4285f4', marginBottom: '6px', fontFamily: 'monospace', letterSpacing: '0.05em' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginTop: '3px', display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
          <span style={{ opacity: 0.7 }}>{p.name}</span><strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

const SectionHeading = ({ icon: Icon, color, label, tag }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
    <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${color}18`, border: `1px solid ${color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Icon size={16} style={{ color }} />
    </div>
    <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', margin: 0, letterSpacing: '0.03em' }}>{label}</h3>
    {tag && (
      <span style={{ marginLeft: 'auto', fontSize: '10px', color, fontFamily: 'monospace', letterSpacing: '0.1em', background: `${color}12`, padding: '3px 8px', borderRadius: '4px', border: `1px solid ${color}25` }}>{tag}</span>
    )}
  </div>
)

const FeatureCard = ({ icon: Icon, color, title, desc }) => (
  <div style={{ padding: '18px', background: 'rgba(255,255,255,0.025)', borderRadius: '10px', border: `1px solid ${color}22`, position: 'relative', overflow: 'hidden' }}>
    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: `linear-gradient(90deg, transparent, ${color}80, transparent)` }} />
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
      <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon size={14} style={{ color }} />
      </div>
      <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>{title}</span>
    </div>
    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.65', margin: 0 }}>{desc}</p>
  </div>
)

const ReqRow = ({ label, value, color = '#4285f4' }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
    <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{label}</span>
    <span style={{ fontSize: '12px', fontFamily: 'monospace', color, background: `${color}12`, padding: '3px 10px', borderRadius: '4px', border: `1px solid ${color}25` }}>{value}</span>
  </div>
)

function Dashboard() {
  const [healthData, setHealthData]     = useState(null)
  const [metricsData, setMetricsData]   = useState(null)
  const [timelineData, setTimelineData] = useState([])
  const [isOffline, setIsOffline]       = useState(false)
  const cardRefs = useRef([])
  const { getInfluence } = useCursorPhysics()

  useEffect(() => {
    const loadData = async () => {
      try {
        const [health, metrics, timeline] = await Promise.all([fetchHealth(), fetchMetrics(), fetchTimeline('24h')])
        if (!health || !metrics || !timeline) { setIsOffline(true); return }
        setHealthData(health)
        setMetricsData(metrics)
        setTimelineData((timeline.timeline || []).map(item => ({
          timestamp: new Date(item.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          packets: item.packets, events: item.events,
        })))
        setIsOffline(false)
      } catch { setIsOffline(true) }
    }
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let frameId
    const applyPhysics = () => {
      cardRefs.current.forEach(ref => {
        if (!ref) return
        const rect = ref.getBoundingClientRect()
        const influence = getInfluence(rect, 200, 8)
        ref.style.transform = `translate(${influence.x}px, ${influence.y}px)`
      })
      frameId = requestAnimationFrame(applyPhysics)
    }
    frameId = requestAnimationFrame(applyPhysics)
    return () => cancelAnimationFrame(frameId)
  }, [getInfluence])

  const cards = [
    { label: 'System Health',    value: healthData?.status === 'ok' ? 'Healthy' : healthData?.status || 'Unknown', subtext: healthData ? `Status: ${healthData.status}` : 'Loading...', icon: Shield,       iconColor: '#34a853', glowColor: 'rgba(52,168,83,0.15)',    className: 'health' },
    { label: 'Total Detections', value: metricsData?.total_detections ?? 0,       subtext: 'All time',             icon: AlertTriangle, iconColor: '#fbbc04', glowColor: 'rgba(251,188,4,0.12)',    className: 'detections' },
    { label: 'Active Risky IPs', value: metricsData?.unique_blocked_ips ?? 0,     subtext: 'Currently monitored',  icon: Globe,         iconColor: '#ea4335', glowColor: 'rgba(234,67,53,0.12)',    className: 'risky' },
    { label: 'Monitor Actions',  value: metricsData?.monitor_actions ?? 'N/A',    subtext: metricsData?.last_detection ? `Last ${new Date(metricsData.last_detection).toLocaleTimeString()}` : 'No detections', icon: Eye, iconColor: '#4285f4', glowColor: 'rgba(66,133,244,0.12)', className: 'confidence' },
  ]

  return (
    <div>
      {isOffline && <div className="demo-banner"><AlertCircle size={16} /> Backend offline — Check API connection</div>}

      {/* ── Metric Cards ── */}
      <div className="metrics-grid">
        {cards.map((card, i) => {
          const Icon = card.icon
          return (
            <div key={i} ref={el => cardRefs.current[i] = el} className={`metric-card ${card.className}`}
              style={{ boxShadow: `0 0 24px ${card.glowColor}`, position: 'relative', overflow: 'hidden' }}>
              <span style={{ position: 'absolute', top: 0, right: 0, width: 0, height: 0, borderStyle: 'solid', borderWidth: '0 28px 28px 0', borderColor: `transparent ${card.iconColor}30 transparent transparent` }} />
              <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Icon size={14} style={{ color: card.iconColor }} />{card.label}
              </div>
              <div className="metric-value">{card.value}</div>
              <div className="metric-subtext">{card.subtext}</div>
              <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: '2px', background: `linear-gradient(90deg, transparent, ${card.iconColor}, transparent)`, opacity: 0.6 }} />
            </div>
          )
        })}
      </div>

      {/* ── Traffic Timeline ── */}
      {timelineData.length > 0 && (
        <div className="chart-container" style={{ background: 'linear-gradient(135deg, rgba(66,133,244,0.04) 0%, rgba(0,0,0,0) 60%)', border: '1px solid rgba(66,133,244,0.2)', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(66,133,244,0.03) 3px, rgba(66,133,244,0.03) 4px)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Activity size={16} style={{ color: '#4285f4' }} />
            <h3 className="chart-title" style={{ margin: 0 }}>Traffic Timeline</h3>
            <span style={{ marginLeft: 'auto', fontSize: '11px', color: '#4285f4', fontFamily: 'monospace', letterSpacing: '0.05em' }}>LIVE · 24H</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="packetsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4285f4" stopOpacity={0.4}/><stop offset="95%" stopColor="#4285f4" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="eventsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ea4335" stopOpacity={0.35}/><stop offset="95%" stopColor="#ea4335" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="timestamp" tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }} axisLine={{ stroke: 'rgba(66,133,244,0.2)' }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.35)', fontFamily: 'monospace' }} axisLine={false} tickLine={false} width={36} />
              <Tooltip content={<CyberTooltip />} />
              <Area type="monotone" dataKey="packets" stroke="#4285f4" strokeWidth={2} fill="url(#packetsGrad)" dot={false} name="Packets" />
              <Area type="monotone" dataKey="events"  stroke="#ea4335" strokeWidth={1.5} fill="url(#eventsGrad)" dot={false} name="Events" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ════ ABOUT ════ */}
      <div style={{ marginTop: '28px', padding: '32px', borderRadius: '14px', background: 'linear-gradient(135deg, rgba(66,133,244,0.07) 0%, rgba(234,67,53,0.03) 100%)', border: '1px solid rgba(66,133,244,0.18)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, width: '3px', height: '100%', background: 'linear-gradient(180deg, #4285f4, #ea4335)' }} />

        <SectionHeading icon={Info} color="#4285f4" label="About Apex-Kinetics" tag="v1.0 · LIVE" />

        {/* Hero */}
        <p style={{ fontSize: '15px', color: 'var(--text-primary)', lineHeight: '1.85', marginBottom: '10px', fontWeight: 500 }}>
          <span style={{ color: '#4285f4', fontWeight: 800 }}>Apex-Kinetics</span> is an autonomous, real-time network
          threat intelligence and response platform — engineered to outpace adversaries at the speed of computation.
        </p>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.85', marginBottom: '28px' }}>
          Built to detect, classify, and neutralise malicious network activity across 5 attack vectors —
          DDoS floods, brute-force intrusions, SQL injection probes, port-scan sweeps, and malware beaconing —
          the system operates continuously with{' '}
          <span style={{ color: '#34a853', fontWeight: 600 }}>zero human intervention</span> required.
          Every packet is a data point. Every anomaly triggers a decision. Every decision is logged.
        </p>

        {/* Feature cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px', marginBottom: '28px' }}>
          <FeatureCard icon={Cpu}      color="#4285f4" title="Detection Engine"       desc="ML-powered multi-vector classification pipeline. Processes live packet streams and flags anomalies with sub-second latency." />
          <FeatureCard icon={Shield}   color="#34a853" title="Autonomous Response"    desc="Instant BLOCK / RATE-LIMIT / MONITOR decisions enforced without human approval. Rules adapt based on cumulative threat score." />
          <FeatureCard icon={Activity} color="#fbbc04" title="Live Traffic Analysis"  desc="Continuous 24/7 packet and security event stream monitoring. Timeline replay across configurable windows: 5m → 30d." />
          <FeatureCard icon={Lock}     color="#ea4335" title="IP Threat Scoring"      desc="Per-IP risk scores (0–100) with confidence metrics, severity classification, and full first/last-seen audit trail." />
          <FeatureCard icon={Database} color="#9c27b0" title="Audit & Forensics"      desc="Every detection and response action is written to an immutable audit log — full forensic trail for compliance and review." />
          <FeatureCard icon={Network}  color="#00bcd4" title="Correlation Engine"     desc="Cross-IP attack pattern correlation detects coordinated campaigns, not just isolated events, for a holistic threat picture." />
        </div>

        {/* Why */}
        <div style={{ padding: '20px 22px', background: 'rgba(66,133,244,0.06)', borderRadius: '10px', border: '1px solid rgba(66,133,244,0.15)', marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <AlertOctagon size={15} style={{ color: '#fbbc04' }} />
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#fbbc04', letterSpacing: '0.08em', textTransform: 'uppercase' }}>Why Apex-Kinetics?</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.85', margin: 0 }}>
            Traditional firewalls and IDS tools react to <em>known</em> signatures — they're blind to zero-day tactics
            and slow to respond to volume attacks. Apex-Kinetics takes a different approach: it correlates multi-vector
            attack patterns in real time, adapts response thresholds dynamically as threat scores accumulate, and maintains
            a living threat map of your network. Whether you're hardening a university lab, a startup backend, or a
            production microservices cluster, Apex-Kinetics delivers{' '}
            <span style={{ color: '#4285f4', fontWeight: 600 }}>full-spectrum situational awareness</span> and automated
            countermeasures at machine speed — not human speed.
          </p>
        </div>

        {/* Use cases */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <BookOpen size={14} style={{ color: '#34a853' }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#34a853', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Use Cases</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
            {[
              { label: 'University / Lab Networks',    color: '#4285f4' },
              { label: 'Startup API Protection',       color: '#34a853' },
              { label: 'Red Team Simulation',          color: '#ea4335' },
              { label: 'SOC Training Environments',    color: '#fbbc04' },
              { label: 'Cloud Infrastructure Defence', color: '#9c27b0' },
              { label: 'IoT Network Monitoring',       color: '#00bcd4' },
            ].map((uc, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 14px', background: `${uc.color}0d`, borderRadius: '8px', border: `1px solid ${uc.color}22` }}>
                <CheckCircle size={13} style={{ color: uc.color, flexShrink: 0 }} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{uc.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', flexWrap: 'wrap', background: 'rgba(0,0,0,0.2)', borderRadius: '10px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.06)', marginBottom: '28px' }}>
          {[
            { label: 'Attack Vectors',  value: '5+',      color: '#4285f4' },
            { label: 'Response Time',   value: '<1s',     color: '#34a853' },
            { label: 'Uptime Target',   value: '99.9%',   color: '#fbbc04' },
            { label: 'Data Retention',  value: '30 days', color: '#ea4335' },
            { label: 'Decision Types',  value: '3',       color: '#9c27b0' },
            { label: 'API Endpoints',   value: '15+',     color: '#00bcd4' },
          ].map((stat, i, arr) => (
            <div key={i} style={{ flex: '1 1 120px', padding: '18px 20px', textAlign: 'center', borderRight: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
              <div style={{ fontSize: '26px', fontWeight: 800, color: stat.color, fontFamily: 'monospace', letterSpacing: '-0.02em' }}>{stat.value}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-secondary)', letterSpacing: '0.08em', textTransform: 'uppercase', marginTop: '4px' }}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* System Requirements */}
        <div style={{ marginBottom: '28px' }}>
          <SectionHeading icon={Settings} color="#fbbc04" label="System Requirements" tag="RECOMMENDED" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div>
              <div style={{ fontSize: '11px', color: '#4285f4', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid rgba(66,133,244,0.2)' }}>Backend</div>
              <ReqRow label="Python"      value="≥ 3.10"    color="#fbbc04" />
              <ReqRow label="FastAPI"     value="≥ 0.100"   color="#4285f4" />
              <ReqRow label="Pandas"      value="≥ 2.0"     color="#34a853" />
              <ReqRow label="Uvicorn"     value="≥ 0.23"    color="#9c27b0" />
              <ReqRow label="RAM"         value="≥ 512 MB"  color="#fbbc04" />
              <ReqRow label="Storage"     value="≥ 1 GB"    color="#ea4335" />
              <ReqRow label="OS"          value="macOS / Linux / Windows" color="#00bcd4" />
            </div>
            <div>
              <div style={{ fontSize: '11px', color: '#ea4335', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid rgba(234,67,53,0.2)' }}>Frontend</div>
              <ReqRow label="Node.js"     value="≥ 18.x"           color="#34a853" />
              <ReqRow label="React"       value="≥ 18"             color="#4285f4" />
              <ReqRow label="Vite"        value="≥ 5"              color="#fbbc04" />
              <ReqRow label="Recharts"    value="≥ 2.8"            color="#9c27b0" />
              <ReqRow label="Browser"     value="Chrome / Safari"  color="#00bcd4" />
              <ReqRow label="Screen"      value="≥ 1280px wide"    color="#ea4335" />
              <ReqRow label="Network"     value="localhost access"  color="#34a853" />
            </div>
          </div>
        </div>

        {/* How it works pipeline */}
        <div>
          <SectionHeading icon={Terminal} color="#00bcd4" label="How It Works" tag="PIPELINE" />
          <div style={{ display: 'flex', alignItems: 'stretch', flexWrap: 'wrap', borderRadius: '10px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.06)' }}>
            {[
              { step: '01', title: 'Ingest',    desc: 'Raw network packets and events are captured and written to the detection pipeline in real time.',   color: '#4285f4' },
              { step: '02', title: 'Classify',  desc: 'The ML engine labels each event: DDoS, brute-force, port-scan, SQL injection, or malware.',         color: '#fbbc04' },
              { step: '03', title: 'Correlate', desc: 'Events are grouped by IP and time window. Cross-IP attack campaigns are identified and flagged.',    color: '#9c27b0' },
              { step: '04', title: 'Score',     desc: 'Each IP receives a 0–100 risk score with confidence level and HIGH / MEDIUM / LOW severity.',        color: '#ea4335' },
              { step: '05', title: 'Respond',   desc: 'Automated BLOCK / RATE-LIMIT / MONITOR is executed instantly and written to the audit log.',         color: '#34a853' },
            ].map((s, i) => (
              <div key={i} style={{ flex: '1 1 150px', padding: '20px 16px', background: `${s.color}07`, borderLeft: `2px solid ${s.color}50`, borderRight: i < 4 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
                <div style={{ fontSize: '20px', fontWeight: 800, color: `${s.color}35`, fontFamily: 'monospace', marginBottom: '6px' }}>{s.step}</div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: s.color, marginBottom: '8px' }}>{s.title}</div>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.65', margin: 0 }}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

export default Dashboard