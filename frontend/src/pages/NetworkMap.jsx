import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Shield, Wifi, Server, Monitor, Network } from 'lucide-react'
import { useDetectionStream } from '../hooks/useDetectionStream'
import './NetworkMap.css'

const TOTAL_DEVICES = 243
const FLASH_MS = 3000

/* Generic business zones — 2x2 topology.
   `id` values match the target_zone field emitted by OrgNetworkProfile
   (scripts/org_profile.py) so an explicit target_zone maps directly. */
const ZONES = [
  { id: 'admin',        name: 'Management Office',     range: '10.0.1.x', octet: 1, Icon: Shield,  assets: ['Executive Systems', 'HR Portal', 'Finance Server'] },
  { id: 'student_wifi', name: 'Guest Network',          range: '10.0.2.x', octet: 2, Icon: Wifi,    assets: ['~200 guest/visitor devices'] },
  { id: 'server_room',  name: 'Server Infrastructure', range: '10.0.3.x', octet: 3, Icon: Server,  assets: ['Web Server', 'Database', 'Application Server'] },
  { id: 'lab',          name: 'Endpoint Network',       range: '10.0.4.x', octet: 4, Icon: Monitor, assets: ['40 workstations'] },
]

/* Map an internal 10.0.N.x address to a zone id, else null */
function ipToZoneId(ip) {
  if (typeof ip !== 'string') return null
  const m = ip.match(/^10\.0\.(\d{1,3})\./)
  if (!m) return null
  const octet = Number(m[1])
  return ZONES.find(z => z.octet === octet)?.id ?? null
}

/* Decide which zone a detection targets:
   1) internal source_ip (10.0.N.x) → that zone
   2) external source_ip + explicit target_zone (id or name) → that zone
   3) external source_ip, no target_zone → random zone (demo) */
function resolveTargetZone(d) {
  const src = d.source_ip || d.ip
  const internal = ipToZoneId(src)
  if (internal) return internal

  const tz = d.target_zone
  if (tz) {
    const byKey = ZONES.find(z => z.id === tz || z.name === tz)
    if (byKey) return byKey.id
    const byIp = ipToZoneId(tz)
    if (byIp) return byIp
  }

  return ZONES[Math.floor(Math.random() * ZONES.length)].id
}

function StatusPill({ status }) {
  const label = status === 'attack' ? 'Under Attack' : status === 'alert' ? 'Alert' : 'Secure'
  return (
    <span className={`netmap-status netmap-status-${status}`}>
      <span className="netmap-status-dot" />
      {label}
    </span>
  )
}

function NetworkMap() {
  const [hits, setHits]               = useState(() => Object.fromEntries(ZONES.map(z => [z.id, 0])))
  const [flashing, setFlashing]       = useState(() => Object.fromEntries(ZONES.map(z => [z.id, false])))
  const [lastAttack, setLastAttack]   = useState(() => Object.fromEntries(ZONES.map(z => [z.id, null])))
  const [threats, setThreats]         = useState(0)
  const [lastUpdated, setLastUpdated] = useState(null)
  const timersRef = useRef({})

  const onDetection = useCallback((d) => {
    if (!d || d.label === 'normal') return
    const zoneId = resolveTargetZone(d)

    setHits(prev => ({ ...prev, [zoneId]: (prev[zoneId] || 0) + 1 }))
    setThreats(t => t + 1)
    setLastUpdated(Date.now())
    setLastAttack(prev => ({ ...prev, [zoneId]: d.label || 'unknown' }))

    setFlashing(prev => ({ ...prev, [zoneId]: true }))
    if (timersRef.current[zoneId]) clearTimeout(timersRef.current[zoneId])
    timersRef.current[zoneId] = setTimeout(() => {
      setFlashing(prev => ({ ...prev, [zoneId]: false }))
    }, FLASH_MS)
  }, [])

  useDetectionStream(onDetection)

  useEffect(() => () => {
    Object.values(timersRef.current).forEach(clearTimeout)
  }, [])

  // attack (currently flashing) > alert (hit before) > secure (never hit)
  const statusOf = (zoneId) => {
    if (flashing[zoneId]) return 'attack'
    if ((hits[zoneId] || 0) > 0) return 'alert'
    return 'secure'
  }

  // Count all zones that have been hit this session (attack + alert)
  const zonesUnderAttack = ZONES.filter(z => statusOf(z.id) !== 'secure').length

  const summary = [
    { label: 'Devices Monitored',  value: TOTAL_DEVICES },
    { label: 'Active Threats',     value: threats },
    { label: 'Zones Under Attack', value: zonesUnderAttack },
    { label: 'Last Updated',       value: lastUpdated
        ? new Date(lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : '—' },
  ]

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '20px' }}>
        <div className="netmap-eyebrow">Topology</div>
        <div className="netmap-title">
          <Network size={18} style={{ opacity: 0.6 }} /> Network Map
        </div>
      </div>

      {/* Network Health summary bar */}
      <div className="netmap-health">
        {summary.map((s, i) => (
          <div className="netmap-health-cell" key={i}>
            <div className="netmap-health-label">{s.label}</div>
            <div className="netmap-health-value">{s.value}</div>
          </div>
        ))}
      </div>

      {/* 2x2 zone grid */}
      <div className="netmap-grid">
        {ZONES.map(zone => {
          const { Icon } = zone
          const status = statusOf(zone.id)
          const count = hits[zone.id] || 0
          const attack = lastAttack[zone.id]
          return (
            <div key={zone.id} className={`netmap-zone netmap-zone-${status}`}>
              <div className="netmap-zone-head">
                <div className="netmap-zone-icon"><Icon size={18} /></div>
                <div className="netmap-zone-heading">
                  <div className="netmap-zone-name">{zone.name}</div>
                  <div className="netmap-zone-range">{zone.range}</div>
                </div>
                <div className="netmap-count-wrap" title="Detections this session">
                  <div className="netmap-count">{count}</div>
                  <div className="netmap-count-sub">this session</div>
                </div>
              </div>

              <div className="netmap-assets">
                {zone.assets.map((a, i) => (
                  <div className="netmap-asset" key={i}>
                    <span className="netmap-asset-dot" />
                    {a}
                  </div>
                ))}
                {attack && (
                  <div className="netmap-last-attack">
                    Last attack: <span className="netmap-last-attack-type">{attack.replace(/_/g, ' ')}</span>
                  </div>
                )}
                {!attack && (
                  <div className="netmap-last-attack" style={{ opacity: 0.35 }}>Last attack: —</div>
                )}
              </div>

              <div className="netmap-zone-foot">
                <StatusPill status={status} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default NetworkMap
