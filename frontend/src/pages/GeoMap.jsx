/**
 * GeoMap — Phase 5A: live world map of attacking IPs.
 *
 * Map approach: centroid-circle dot-grid.
 * Each country is represented by a semi-transparent circle centred on its
 * geographic centroid, sized proportionally to approximate land area.
 * This avoids embedding 200 KB+ of SVG path data while still providing clear
 * geographic context. Attack point markers overlay the map at exact lat/lon.
 *
 * Coordinate projection (equirectangular, viewBox "0 0 1000 500"):
 *   x = (lon + 180) × (1000 / 360)
 *   y = (90 − lat)  × (500 / 180)
 */
import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useDetectionStream } from '../hooks/useDetectionStream'
import { getFlag, getCountryName } from '../utils/countryFlags'
import { fetchGeoAttackers, fetchGeoSummary } from '../api/api'
import './GeoMap.css'

// [iso_code, lat, lon, radius] — radius ≈ sqrt(land_area) normalised to 4–36
const COUNTRIES = [
  ['RU', 61.5,  100.0, 34], ['CA', 56.1, -106.3, 28], ['US', 38.0,  -97.0, 26],
  ['CN', 35.0,  103.0, 24], ['BR', -14.2, -51.9, 24], ['AU', -25.3, 133.8, 24],
  ['IN', 20.6,   78.9, 20], ['AR', -38.4, -63.6, 20], ['KZ', 48.0,   68.0, 20],
  ['DZ', 28.0,    2.6, 18], ['SA', 24.0,  45.0,  17], ['MX', 23.6, -102.6, 17],
  ['ID', -0.8,  113.9, 17], ['LY', 26.3,  17.2,  15], ['IR', 32.4,  53.7,  15],
  ['MN', 46.8,  103.8, 15], ['SD', 12.9,  30.2,  14], ['DE', 51.2,  10.5,  10],
  ['UA', 48.4,   31.2, 13], ['FR', 46.2,   2.2,  10], ['AF', 33.9,  67.7,  12],
  ['PK', 30.4,   69.3, 12], ['TR', 38.9,  35.2,  12], ['NG', 9.1,    8.7,  12],
  ['ET', 9.1,   40.5,  11], ['ZA', -30.6, 22.9,  12], ['TZ', -6.4,  34.9,  11],
  ['CO', 4.6,  -74.3,  10], ['PE', -9.2,  -75.0, 12], ['EG', 26.8,  30.8,  12],
  ['GB', 55.4,   -3.4,  8], ['PL', 51.9,  19.1,  10], ['RO', 45.9,  24.9,   8],
  ['JP', 36.2,  138.3,  9], ['VN', 14.1,  108.3,  8], ['PH', 12.9,  121.8,  8],
  ['MY', 2.5,   112.5,  8], ['TH', 15.9,  100.9,  8], ['SE', 60.1,  18.6,  10],
  ['NO', 60.5,    8.5, 10], ['FI', 61.9,  25.7,  10], ['IT', 41.9,  12.6,   8],
  ['ES', 40.5,   -3.7,  8], ['BD', 23.7,  90.4,   6], ['KR', 35.9, 127.8,   6],
  ['SG', 1.4,   103.8,  3], ['HK', 22.3,  114.2,  2], ['NL', 52.1,   5.3,   5],
  ['HU', 47.2,   19.5,  5], ['CZ', 50.1,  15.5,   5], ['BE', 50.5,   4.5,   4],
  ['AT', 47.5,   14.6,  5], ['CH', 46.8,   8.2,   4], ['PT', 39.4,  -8.2,   5],
  ['GR', 39.0,   22.0,  6], ['IQ', 33.2,  43.7,  10], ['SY', 35.0,  38.0,   8],
  ['YE', 15.6,   48.5,  9], ['MA', 32.0,  -5.0,  10], ['TN', 34.0,   9.0,   7],
]

function toSvg(lat, lon) {
  return {
    x: (lon + 180) * (1000 / 360),
    y: (90 - lat)  * (500 / 180),
  }
}

function countryFill(count) {
  if (count === 0)  return 'rgba(255,255,255,0.04)'
  if (count <= 5)   return 'rgba(255,100,100,0.28)'
  if (count <= 20)  return 'rgba(255,60,60,0.50)'
  return                   'rgba(255,30,30,0.78)'
}

function timeAgo(ts) {
  if (!ts) return '—'
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (s < 60)  return `${s}s ago`
  if (s < 3600) return `${Math.floor(s/60)}m ago`
  return `${Math.floor(s/3600)}h ago`
}

const MAX_FEED = 20
const MAX_POINTS = 400   // cap SVG markers for performance

export default function GeoMap() {
  // ip → { lat, lon, country_code, country_name, city, isp, label, count, last_seen, pulse }
  const [attackPoints,  setAttackPoints]  = useState(() => new Map())
  // country_code → { count, last_seen, country_name }
  const [countryCounts, setCountryCounts] = useState(() => new Map())
  const [summary,       setSummary]       = useState(null)
  const [timeFilter,    setTimeFilter]    = useState('all')
  const [isLive,        setIsLive]        = useState(true)
  const [tooltip,       setTooltip]       = useState(null)
  const [recentFeed,    setRecentFeed]    = useState([])
  const pulseTimers = useRef({})

  // ── Load historical data on mount ────────────────────────────────────────
  useEffect(() => {
    fetchGeoAttackers().then(data => {
      if (!Array.isArray(data)) return
      const points = new Map()
      const counts = new Map()
      const cutoff = cutoffTime(timeFilter)
      data.forEach(d => {
        if (cutoff && d.last_seen && d.last_seen < cutoff) return
        points.set(d.ip, {
          lat: d.lat, lon: d.lon,
          country_code: d.country_code, country_name: getCountryName(d.country_code),
          city: d.city, isp: '', label: d.attack_type,
          count: d.count, last_seen: d.last_seen, pulse: false,
        })
        const cc = d.country_code
        if (cc) {
          const prev = counts.get(cc) || { count: 0, last_seen: null, country_name: getCountryName(cc) }
          counts.set(cc, {
            count: prev.count + d.count,
            last_seen: d.last_seen,
            country_name: prev.country_name,
          })
        }
      })
      setAttackPoints(points)
      setCountryCounts(counts)
    }).catch(() => {})

    fetchGeoSummary().then(d => { if (d) setSummary(d) }).catch(() => {})
  }, [timeFilter]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Real-time WebSocket updates ───────────────────────────────────────────
  const onDetection = useCallback((det) => {
    if (!isLive) return
    const geo = det.geo
    if (!geo || geo.lat == null) return

    const ip = det.ip
    const cc = geo.country_code

    setAttackPoints(prev => {
      const next = new Map(prev)
      // Enforce cap — evict oldest if over limit
      if (!next.has(ip) && next.size >= MAX_POINTS) {
        const oldest = [...next.entries()].sort((a,b) => (a[1].last_seen||'') - (b[1].last_seen||''))[0]
        if (oldest) next.delete(oldest[0])
      }
      const existing = next.get(ip) || { count: 0 }
      next.set(ip, {
        lat: geo.lat, lon: geo.lon,
        country_code: cc, country_name: geo.country_name || getCountryName(cc),
        city: geo.city, isp: geo.isp,
        label: det.label, count: existing.count + 1,
        last_seen: det.timestamp, pulse: true,
      })
      return next
    })

    if (cc) {
      setCountryCounts(prev => {
        const next = new Map(prev)
        const p = next.get(cc) || { count: 0, last_seen: null, country_name: getCountryName(cc) }
        next.set(cc, { count: p.count + 1, last_seen: det.timestamp, country_name: p.country_name })
        return next
      })
    }

    setRecentFeed(prev => [{
      id: `${ip}-${det.timestamp}`,
      ip, label: det.label, flag: getFlag(cc),
      city: geo.city, country_code: cc, timestamp: det.timestamp,
    }, ...prev].slice(0, MAX_FEED))

    // Remove pulse after animation completes
    clearTimeout(pulseTimers.current[ip])
    pulseTimers.current[ip] = setTimeout(() => {
      setAttackPoints(prev => {
        const next = new Map(prev)
        const pt = next.get(ip)
        if (pt) next.set(ip, { ...pt, pulse: false })
        return next
      })
    }, 1500)
  }, [isLive])

  useDetectionStream(onDetection)

  // ── Derived stats ─────────────────────────────────────────────────────────
  const countriesDetected = countryCounts.size
  const topCountry = [...countryCounts.entries()].sort((a,b) => b[1].count - a[1].count)[0]
  const attacksMapped = [...attackPoints.values()].reduce((s,p) => s + p.count, 0)
  const coverage = summary ? `${Math.round((summary.coverage_rate || 0) * 100)}%` : '—'

  // ── Sorted countries for table ────────────────────────────────────────────
  const sortedCountries = [...countryCounts.entries()]
    .sort((a,b) => b[1].count - a[1].count)
    .slice(0, 10)

  return (
    <div className="geo-map-page">
      <div className="geo-map-title">Geo Map — Attacker Origins</div>

      {/* Stats bar */}
      <div className="geo-stats">
        <div className="geo-stat-card">
          <div className="geo-stat-label">Countries Detected</div>
          <div className="geo-stat-value">{countriesDetected}</div>
          <div className="geo-stat-sub">unique origin countries</div>
        </div>
        <div className="geo-stat-card">
          <div className="geo-stat-label">Most Active</div>
          <div className="geo-stat-value" style={{ fontSize: '18px' }}>
            {topCountry
              ? `${getFlag(topCountry[0])} ${getCountryName(topCountry[0])}`
              : '—'}
          </div>
          <div className="geo-stat-sub">
            {topCountry ? `${topCountry[1].count} attacks` : 'no data yet'}
          </div>
        </div>
        <div className="geo-stat-card">
          <div className="geo-stat-label">Attacks Mapped</div>
          <div className="geo-stat-value">{attacksMapped}</div>
          <div className="geo-stat-sub">geolocated events</div>
        </div>
        <div className="geo-stat-card">
          <div className="geo-stat-label">Coverage</div>
          <div className="geo-stat-value">{coverage}</div>
          <div className="geo-stat-sub">IPs with geo data</div>
        </div>
      </div>

      {/* World Map */}
      <div className="geo-map-container">
        <svg
          viewBox="0 0 1000 500"
          className="world-svg"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Ocean */}
          <rect x="0" y="0" width="1000" height="500" fill="#070d1a" />

          {/* Grid: equator + prime meridian */}
          <line x1="0" y1="250" x2="1000" y2="250" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" strokeDasharray="4 4" />
          <line x1="500" y1="0" x2="500" y2="500" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" strokeDasharray="4 4" />

          {/* Country centroid circles */}
          {COUNTRIES.map(([code, lat, lon, r]) => {
            const { x, y } = toSvg(lat, lon)
            const cnt = countryCounts.get(code)?.count || 0
            return (
              <circle
                key={code}
                cx={x} cy={y} r={r}
                fill={countryFill(cnt)}
                stroke="rgba(255,255,255,0.06)"
                strokeWidth="0.4"
                className="country-dot"
              />
            )
          })}

          {/* Attack point markers */}
          {[...attackPoints.values()].map((pt) => {
            const { x, y } = toSvg(pt.lat, pt.lon)
            return (
              <g
                key={pt.ip || `${pt.lat}-${pt.lon}`}
                className="attack-marker"
                onMouseEnter={(e) => setTooltip({ pt, mx: e.clientX, my: e.clientY })}
                onMouseLeave={() => setTooltip(null)}
              >
                {pt.pulse && (
                  <circle cx={x} cy={y} r="5" fill="none"
                    stroke="#ff4444" strokeWidth="1.5"
                    className="pulse-ring"
                  />
                )}
                <circle
                  cx={x} cy={y}
                  r={pt.pulse ? 5 : 3.5}
                  fill="#ff3333"
                  opacity="0.85"
                  className="attack-core"
                  style={{ transition: 'r 0.3s' }}
                />
              </g>
            )
          })}
        </svg>

        {/* Controls */}
        <div className="geo-controls">
          <div className="geo-live-indicator">
            <span className={`geo-live-dot ${isLive ? 'blinking' : 'paused'}`} />
            {isLive ? 'LIVE' : 'PAUSED'}
          </div>
          <button
            className={`geo-ctrl-btn ${isLive ? 'active' : ''}`}
            onClick={() => setIsLive(v => !v)}
          >
            {isLive ? 'Pause' : 'Resume'}
          </button>
          {['1h', '24h', 'all'].map(f => (
            <button
              key={f}
              className={`geo-ctrl-btn ${timeFilter === f ? 'active' : ''}`}
              onClick={() => setTimeFilter(f)}
            >
              {f === 'all' ? 'ALL' : `Last ${f}`}
            </button>
          ))}
        </div>
      </div>

      {/* Bottom: countries table + live feed */}
      <div className="geo-bottom">
        {/* Top countries */}
        <div className="geo-countries-card">
          <div className="geo-card-header">Top Countries</div>
          {sortedCountries.length === 0 ? (
            <div className="geo-empty">Waiting for geolocated attacks…</div>
          ) : (
            <table className="geo-table">
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Attacks</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {sortedCountries.map(([code, info]) => (
                  <tr key={code}>
                    <td>{getFlag(code)} {info.country_name || getCountryName(code)}</td>
                    <td><span className="geo-count-badge">{info.count}</span></td>
                    <td style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)' }}>
                      {timeAgo(info.last_seen)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Live geo feed */}
        <div className="geo-feed-card">
          <div className="geo-card-header">Recent Geolocated Attacks</div>
          {recentFeed.length === 0 ? (
            <div className="geo-empty">
              {attackPoints.size > 0
                ? 'Historical data loaded — waiting for new events…'
                : 'Waiting for geolocated attacks…'}
            </div>
          ) : (
            <div className="geo-feed-list">
              {recentFeed.map(item => (
                <div key={item.id} className="geo-feed-item">
                  <span className="geo-feed-flag">{item.flag || '🌐'}</span>
                  <span className="geo-feed-label">{item.label.replace(/_/g, ' ')}</span>
                  <span className="geo-feed-location">
                    {[item.city, getCountryName(item.country_code)].filter(Boolean).join(', ')}
                  </span>
                  <span className="geo-feed-ip">{item.ip}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div className="geo-tooltip" style={{ left: tooltip.mx + 12, top: tooltip.my - 8 }}>
          <div className="geo-tooltip-label">{tooltip.pt.label?.replace(/_/g, ' ')}</div>
          <div>
            {getFlag(tooltip.pt.country_code)}{' '}
            {[tooltip.pt.city, getCountryName(tooltip.pt.country_code)].filter(Boolean).join(', ')}
          </div>
          <div className="geo-tooltip-ip">
            {tooltip.pt.ip} · {tooltip.pt.count} attack{tooltip.pt.count !== 1 ? 's' : ''}
          </div>
          {tooltip.pt.isp && (
            <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)' }}>
              {tooltip.pt.isp}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function cutoffTime(filter) {
  if (filter === 'all') return null
  const h = filter === '1h' ? 1 : 24
  return new Date(Date.now() - h * 3600 * 1000).toISOString()
}
