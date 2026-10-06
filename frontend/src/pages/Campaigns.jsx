/**
 * Campaigns — Phase 5B: live multi-stage attack campaign correlation.
 *
 * Active campaigns render as live cards with a kill-chain progress indicator;
 * completed campaigns fall into a sortable table below. Real-time updates
 * arrive via the shared detection WebSocket ({type:"campaign_update"}); a 10 s
 * poll of /api/campaigns reconciles state so the page is correct even if a WS
 * message is missed.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { GitBranch, Printer } from 'lucide-react'
import { useDetectionStream } from '../hooks/useDetectionStream'
import { getFlag, getCountryName } from '../utils/countryFlags'
import { fetchCampaigns, fetchCampaignStats, resolveCampaign } from '../api/api'
import './Campaigns.css'

const KILL_CHAIN = ['Recon', 'Access', 'Execute', 'Impact']

function timeAgo(ts) {
  if (!ts) return '—'
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (s < 60)   return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  return `${Math.floor(s / 3600)}h ago`
}

function duration(start, end) {
  if (!start || !end) return '—'
  const mins = Math.round((new Date(end) - new Date(start)) / 60000)
  if (mins < 1) return '<1 min'
  if (mins < 60) return `${mins} min`
  return `${(mins / 60).toFixed(1)}h`
}

function typeLabel(t) {
  return { multi_vector: 'Multi-Vector', kill_chain: 'Kill Chain', high_volume: 'High Volume' }[t] || t
}

/* ── Kill chain progress indicator (pure CSS) ─────────────────────────────── */
function KillChain({ stages }) {
  const done = new Set(stages || [])
  return (
    <div className="camp-chain">
      {KILL_CHAIN.map((name) => {
        const filled = done.has(name)
        return (
          <div key={name} className="camp-chain-stage">
            <div className={`camp-chain-line ${filled ? 'filled' : ''}`} />
            <div className={`camp-chain-node ${filled ? 'filled' : ''}`} />
            <div className={`camp-chain-label ${filled ? 'filled' : ''}`}>{name}</div>
          </div>
        )
      })}
    </div>
  )
}

const CampaignCard = React.memo(function CampaignCard({ c, flash, onResolve }) {
  const seq = (c.attack_types || []).map(t => t.replace(/_/g, ' '))
  return (
    <div className={`camp-card sev-${c.severity} ${flash ? 'flash' : ''}`}>
      <div className="camp-card-top">
        <span className="camp-badge active"><span className="dot" />Active</span>
        <span className="camp-badge type">{typeLabel(c.campaign_type)}</span>
        <span className={`camp-badge sev-${c.severity}`}>{c.severity}</span>
      </div>

      <div className="camp-card-ip">
        {c.source_ip}
        {c.geo_country && (
          <span className="camp-card-geo">
            {getFlag(c.geo_country.length === 2 ? c.geo_country : '')} {c.geo_country}
          </span>
        )}
      </div>

      <KillChain stages={c.mitre_stages} />

      <div className="camp-sequence">
        {seq.map((s, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="camp-seq-arrow">→</span>}
            {s}
          </React.Fragment>
        ))}
      </div>

      <div className="camp-card-foot">
        <span className="camp-card-meta">
          Started {timeAgo(c.started_at)} · {c.total_detections} detection{c.total_detections !== 1 ? 's' : ''}
        </span>
        <button className="camp-resolve-btn" onClick={() => onResolve(c.id)}>Resolve</button>
      </div>
    </div>
  )
})

export default function Campaigns() {
  const [active, setActive]       = useState([])
  const [completed, setCompleted] = useState([])
  const [stats, setStats]         = useState(null)
  const [flashIds, setFlashIds]   = useState(() => new Set())
  const [showCompleted, setShowCompleted] = useState(false)
  const completedSentinelRef = useRef(null)
  const [sortKey, setSortKey]     = useState('started_at')
  const flashTimers = useRef({})

  const refresh = useCallback(async (includeCompleted = false) => {
    const requests = [
      fetchCampaigns('active', 100).catch(() => []),
      fetchCampaignStats().catch(() => null),
    ]
    if (includeCompleted) requests.push(fetchCampaigns('completed', 100).catch(() => []))
    const [act, st, comp] = await Promise.all(requests)
    if (Array.isArray(act))  setActive(act)
    if (st)                  setStats(st)
    if (Array.isArray(comp)) setCompleted(comp)
  }, [])

  // Initial load + 10 s reconcile poll (staggered start)
  useEffect(() => {
    const delay = Math.random() * 2000
    let iv
    const t = setTimeout(() => {
      refresh(showCompleted)
      iv = setInterval(() => refresh(showCompleted), 10000)
    }, delay)
    return () => { clearTimeout(t); clearInterval(iv) }
  }, [refresh, showCompleted])

  // IntersectionObserver — load completed campaigns only when scrolled into view
  useEffect(() => {
    const el = completedSentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setShowCompleted(true); observer.disconnect() }
    }, { threshold: 0.1 })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Cleanup flash timers on unmount
  useEffect(() => {
    return () => { Object.values(flashTimers.current).forEach(clearTimeout) }
  }, [])

  const flash = useCallback((id) => {
    setFlashIds(prev => new Set(prev).add(id))
    clearTimeout(flashTimers.current[id])
    flashTimers.current[id] = setTimeout(() => {
      setFlashIds(prev => { const n = new Set(prev); n.delete(id); return n })
    }, 2000)
  }, [])

  // Real-time WebSocket handler — only processes campaign_update messages
  const onDetection = useCallback((msg) => {
    if (msg.type !== 'campaign_update') return
    const id = msg.campaign_id

    if (msg.status === 'completed') {
      setActive(prev => prev.filter(c => c.id !== id))
      refresh()   // pull the completed record into the table
      return
    }

    setActive(prev => {
      const idx = prev.findIndex(c => c.id === id)
      const card = {
        id,
        source_ip: msg.source_ip,
        campaign_type: msg.campaign_type,
        severity: msg.severity,
        stage_count: msg.stage_count,
        attack_types: msg.attack_types || msg.attack_sequence || [],
        mitre_stages: msg.mitre_stages || [],
        total_detections: msg.total_detections ?? (idx >= 0 ? prev[idx].total_detections : 0),
        geo_country: msg.geo_country,
        started_at: msg.started_at || (idx >= 0 ? prev[idx].started_at : new Date().toISOString()),
        last_seen_at: msg.last_seen_at,
        status: 'active',
      }
      if (idx >= 0) {
        const next = [...prev]; next[idx] = { ...prev[idx], ...card }; return next
      }
      flash(id)   // new campaign
      return [card, ...prev]
    })
  }, [refresh, flash])

  useDetectionStream(onDetection)

  const handleResolve = async (id) => {
    try {
      await resolveCampaign(id)
      setActive(prev => prev.filter(c => c.id !== id))
      refresh()
    } catch (_) { /* ignore */ }
  }

  // Stats derived values
  const activeCount = stats?.active_campaigns ?? active.length
  const completedToday = completed.filter(c => {
    if (!c.ended_at) return false
    return new Date(c.ended_at).toDateString() === new Date().toDateString()
  }).length
  const avgDuration = stats?.avg_duration_minutes != null ? `${stats.avg_duration_minutes} min` : '—'
  const topType = stats?.most_common_type ? typeLabel(stats.most_common_type) : '—'

  const sortedCompleted = [...completed].sort((a, b) => {
    if (sortKey === 'started_at') return (b.started_at || '').localeCompare(a.started_at || '')
    if (sortKey === 'total_detections') return (b.total_detections || 0) - (a.total_detections || 0)
    return 0
  })

  return (
    <div className="campaigns-page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div className="camp-title">Attack Campaigns — Correlation Engine</div>
        <button onClick={() => window.print()} className="time-btn print-hide" title="Export this view to PDF"
          style={{ display: 'flex', alignItems: 'center', gap: '7px', padding: '8px 14px', textTransform: 'none', letterSpacing: '0.02em' }}>
          <Printer size={13} /> Export
        </button>
      </div>

      {/* Stat cards */}
      <div className="camp-stats">
        <div className={`camp-stat-card ${activeCount > 0 ? 'alert' : ''}`}>
          <div className="camp-stat-label">Active Campaigns</div>
          <div className="camp-stat-value">{activeCount}</div>
          <div className="camp-stat-sub">{activeCount > 0 ? 'coordinated attacks in progress' : 'all clear'}</div>
        </div>
        <div className="camp-stat-card">
          <div className="camp-stat-label">Completed Today</div>
          <div className="camp-stat-value">{completedToday}</div>
          <div className="camp-stat-sub">resolved or timed out</div>
        </div>
        <div className="camp-stat-card">
          <div className="camp-stat-label">Avg Duration</div>
          <div className="camp-stat-value" style={{ fontSize: '20px' }}>{avgDuration}</div>
          <div className="camp-stat-sub">campaign lifespan</div>
        </div>
        <div className="camp-stat-card">
          <div className="camp-stat-label">Most Common</div>
          <div className="camp-stat-value" style={{ fontSize: '18px' }}>{topType}</div>
          <div className="camp-stat-sub">dominant campaign type</div>
        </div>
      </div>

      {/* Active campaigns */}
      <div>
        <div className="camp-section-header">
          <GitBranch size={13} />
          Active Campaigns
          {active.length > 0 && <span className="camp-section-count">{active.length}</span>}
        </div>
        {active.length === 0 ? (
          <div className="camp-empty">No active campaigns — waiting for coordinated attack patterns…</div>
        ) : (
          <div className="camp-cards">
            {active.map(c => (
              <CampaignCard key={c.id} c={c} flash={flashIds.has(c.id)} onResolve={handleResolve} />
            ))}
          </div>
        )}
      </div>

      {/* Completed table — lazy: only fetched once scrolled into view */}
      <div ref={completedSentinelRef}>
        <div className="camp-section-header">Completed Campaigns</div>
        {!showCompleted ? (
          <div className="camp-empty" style={{ cursor: 'default' }}>Scroll to load completed campaigns…</div>
        ) : (
        <div className="camp-table-card">
          {sortedCompleted.length === 0 ? (
            <div className="camp-empty">No completed campaigns yet.</div>
          ) : (
            <table className="camp-table">
              <thead>
                <tr>
                  <th>IP</th>
                  <th>Type</th>
                  <th>Stages</th>
                  <th>Duration</th>
                  <th onClick={() => setSortKey('total_detections')}>Detections</th>
                  <th>Country</th>
                  <th onClick={() => setSortKey('started_at')}>Ended</th>
                </tr>
              </thead>
              <tbody>
                {sortedCompleted.map(c => (
                  <tr key={c.id}>
                    <td style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: '11px' }}>{c.source_ip}</td>
                    <td><span className="camp-type-chip">{typeLabel(c.campaign_type)}</span></td>
                    <td>{c.stage_count}/4</td>
                    <td>{duration(c.started_at, c.ended_at)}</td>
                    <td>{c.total_detections}</td>
                    <td style={{ fontSize: '11px' }}>{c.geo_country || '—'}</td>
                    <td style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>{timeAgo(c.ended_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        )}
      </div>
    </div>
  )
}
