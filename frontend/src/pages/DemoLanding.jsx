import React, { useState, useEffect, useRef } from 'react'
import { fetchMetrics, fetchSystemOverview, API_BASE } from '../api/api'
import { useCountUp } from '../hooks/useCountUp'
import './DemoLanding.css'

const MAX_FEED = 5

function timeAgo(ts) {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (diff < 5)  return 'just now'
  if (diff < 60) return `${diff} seconds ago`
  const m = Math.floor(diff / 60)
  if (m < 60)    return `${m} minute${m !== 1 ? 's' : ''} ago`
  const h = Math.floor(m / 60)
  return `${h} hour${h !== 1 ? 's' : ''} ago`
}

function threatClass(level) {
  const l = (level || '').toUpperCase()
  if (l === 'CRITICAL') return 'dl-threat-critical'
  if (l === 'HIGH')     return 'dl-threat-high'
  if (l === 'ELEVATED') return 'dl-threat-elevated'
  return 'dl-threat-low'
}

function useClock() {
  const [time, setTime] = useState(() => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
  useEffect(() => {
    const iv = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    }, 1000)
    return () => clearInterval(iv)
  }, [])
  return time
}

function DemoLanding() {
  const [metrics, setMetrics]     = useState(null)
  const [overview, setOverview]   = useState(null)
  const [feed, setFeed]           = useState([])
  const [lastAttack, setLastAttack] = useState(null)
  const [now, setNow]             = useState(Date.now())

  const clock = useClock()

  const totalDetections = useCountUp(typeof metrics?.total_detections === 'number' ? metrics.total_detections : null)
  const blockedIPs      = useCountUp(typeof overview?.blocked_ips === 'number' ? overview.blocked_ips : null)

  // Update "time ago" every 5s
  useEffect(() => {
    const iv = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(iv)
  }, [])

  // Poll metrics + overview every 5s
  useEffect(() => {
    const poll = async () => {
      try {
        const [m, o] = await Promise.all([
          fetchMetrics().catch(() => null),
          fetchSystemOverview().catch(() => null),
        ])
        if (m) setMetrics(m)
        if (o) setOverview(o)
      } catch { }
    }
    poll()
    const iv = setInterval(poll, 5000)
    return () => clearInterval(iv)
  }, [])

  // WebSocket for live feed
  useEffect(() => {
    const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws/detections'
    let ws
    let dead = false

    const connect = () => {
      if (dead) return
      ws = new WebSocket(wsUrl)

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'detection') {
            const entry = {
              id: `${msg.ip}-${msg.timestamp}`,
              label:  msg.label,
              ip:     msg.ip,
              action: msg.action,
              timestamp: msg.timestamp,
            }
            setFeed(prev => [entry, ...prev].slice(0, MAX_FEED))
            setLastAttack(entry)
          }
        } catch { }
      }

      ws.onclose = () => { if (!dead) setTimeout(connect, 3000) }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => { dead = true; ws?.close() }
  }, [])

  const threatLevel = overview?.threat_level || '—'

  return (
    <div className="demo-landing">
      {/* Header */}
      <header className="dl-header">
        <div className="dl-header-brand">
          <span className="dl-brand-name">APEX ARGUS</span>
          <span className="dl-brand-sub">SOC Platform</span>
        </div>

        <div className="dl-header-center">
          <div className="dl-header-title">Live Threat Monitoring</div>
        </div>

        <div className="dl-header-right">
          <div className="dl-clock">{clock}</div>
          <div className="dl-live-badge">
            <span className="dl-live-dot" />
            LIVE
          </div>
        </div>
      </header>

      <div className="dl-main">
        {/* 2×2 grid */}
        <div className="dl-grid">
          {/* Threats Detected */}
          <div className="dl-card">
            <div className="dl-card-label">Threats Detected</div>
            <div className="dl-card-value">{totalDetections ?? '—'}</div>
            <div className="dl-card-sub">all time</div>
          </div>

          {/* IPs Blocked */}
          <div className="dl-card">
            <div className="dl-card-label">IPs Blocked</div>
            <div className="dl-card-value">{blockedIPs ?? '—'}</div>
            <div className="dl-card-sub">automatically blocked</div>
          </div>

          {/* Threat Level */}
          <div className="dl-card">
            <div className="dl-card-label">Threat Level</div>
            <div className={`dl-threat-level ${threatClass(threatLevel)}`}>
              {threatLevel}
            </div>
            <div className="dl-card-sub">current environment status</div>
          </div>

          {/* Last Attack */}
          <div className="dl-card">
            <div className="dl-card-label">Last Attack</div>
            {lastAttack ? (
              <>
                <div className="dl-last-attack">
                  {lastAttack.label.replace(/_/g, ' ')}
                </div>
                <div className="dl-last-attack-meta">
                  {lastAttack.ip} · {timeAgo(lastAttack.timestamp)}
                </div>
              </>
            ) : (
              <div style={{ fontSize: '1.4rem', color: 'rgba(255,255,255,0.25)', fontWeight: 400 }}>
                awaiting events…
              </div>
            )}
          </div>
        </div>

        {/* Live feed */}
        <div>
          <div className="dl-feed-header">Live Attack Feed</div>
          <div className="dl-feed">
            {feed.length === 0 ? (
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.22)', padding: '8px 0' }}>
                awaiting detections…
              </div>
            ) : (
              feed.map(item => (
                <div key={item.id} className="dl-feed-card">
                  <span className={`dl-feed-badge ${item.action}`}>
                    {item.label.replace(/_/g, ' ')}
                  </span>
                  <span className="dl-feed-ip">{item.ip}</span>
                  <span className="dl-feed-time">{timeAgo(item.timestamp)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="dl-footer">
        <span>Powered by Apex Argus SOC Platform</span>
        <span>apex-argus.io</span>
      </footer>
    </div>
  )
}

export default DemoLanding
