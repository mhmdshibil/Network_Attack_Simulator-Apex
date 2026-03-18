import React, { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertCircle, Wifi } from 'lucide-react'
import { fetchTimeline } from '../api/api'

const CyberTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'rgba(0,0,0,0.92)',
      border: '1px solid #4285f4',
      borderRadius: '6px',
      padding: '10px 14px',
      fontSize: '13px',
      color: '#e8eaed',
      boxShadow: '0 0 20px rgba(66,133,244,0.35)',
    }}>
      <div style={{ color: '#4285f4', marginBottom: '6px', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, marginTop: '3px', display: 'flex', justifyContent: 'space-between', gap: '16px' }}>
          <span style={{ opacity: 0.7 }}>{p.name}</span>
          <strong>{p.value}</strong>
        </div>
      ))}
    </div>
  )
}

function LiveTraffic() {
  const [timeRange, setTimeRange] = useState('24h')
  const [data, setData] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await fetchTimeline(timeRange)
        const mapped = (result.timeline || []).map(item => ({
          timestamp: new Date(item.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          packet_count: item.packets,
          event_count: item.events
        }))
        setData(mapped)
        setError(null)
      } catch (err) {
        setError(err.message)
      }
    }

    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [timeRange])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px', fontFamily: 'var(--font-main)', letterSpacing: '0.02em' }}>
            Live Traffic Monitor
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '16px', fontFamily: 'var(--font-main)' }}>
            Real-time network activity visualization
          </p>
        </div>
        <div className="time-range-buttons">
          <button className={`time-btn ${timeRange === '5m'  ? 'active' : ''}`} onClick={() => setTimeRange('5m')}>5 Minutes</button>
          <button className={`time-btn ${timeRange === '1h'  ? 'active' : ''}`} onClick={() => setTimeRange('1h')}>1 Hour</button>
          <button className={`time-btn ${timeRange === '24h' ? 'active' : ''}`} onClick={() => setTimeRange('24h')}>24 Hours</button>
        </div>
      </div>

      {error && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline — Check your API connection
        </div>
      )}

      {data.length > 0 ? (
        <div className="chart-container" style={{
          background: 'linear-gradient(135deg, rgba(66,133,244,0.04) 0%, rgba(0,0,0,0) 60%)',
          border: '1px solid rgba(66,133,244,0.2)',
          position: 'relative',
          overflow: 'hidden',
        }}>
          {/* scan-line overlay */}
          <div style={{
            position: 'absolute', inset: 0, pointerEvents: 'none',
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(66,133,244,0.03) 3px, rgba(66,133,244,0.03) 4px)',
          }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
            <Wifi size={18} style={{ color: '#4285f4' }} />
            <h3 className="chart-title" style={{ margin: 0 }}>Traffic Over Time</h3>
            <span style={{
              marginLeft: 'auto', fontSize: '12px', color: '#4285f4',
              fontFamily: 'var(--font-mono)', letterSpacing: '0.06em',
              background: 'rgba(66,133,244,0.1)', padding: '3px 10px',
              borderRadius: '4px', border: '1px solid rgba(66,133,244,0.2)',
            }}>
              LIVE · {timeRange.toUpperCase()}
            </span>
          </div>

          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="packetGradLT" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4285f4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#4285f4" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="eventGradLT" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ea4335" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#ea4335" stopOpacity={0} />
                </linearGradient>
              </defs>

              {/* No CartesianGrid — clean cyber look */}
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.35)', fontFamily: 'var(--font-mono)' }}
                axisLine={{ stroke: 'rgba(66,133,244,0.2)' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'rgba(255,255,255,0.35)', fontFamily: 'var(--font-mono)' }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip content={<CyberTooltip />} />

              <Area
                type="monotone"
                dataKey="packet_count"
                stroke="#4285f4"
                strokeWidth={2}
                fill="url(#packetGradLT)"
                dot={false}
                name="Packets"
              />
              <Area
                type="monotone"
                dataKey="event_count"
                stroke="#ea4335"
                strokeWidth={1.5}
                fill="url(#eventGradLT)"
                dot={false}
                name="Events"
              />
            </AreaChart>
          </ResponsiveContainer>

          {/* Legend */}
          <div style={{ display: 'flex', gap: '24px', marginTop: '16px', justifyContent: 'center' }}>
            {[{ color: '#4285f4', label: 'Packets' }, { color: '#ea4335', label: 'Events' }].map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-secondary)', fontFamily: 'var(--font-main)', fontWeight: 600 }}>
                <div style={{ width: '24px', height: '2px', background: item.color, borderRadius: '2px' }} />
                {item.label}
              </div>
            ))}
          </div>
        </div>
      ) : (
        !error && (
          <div className="chart-container" style={{ textAlign: 'center', padding: '60px', color: 'var(--text-secondary)', fontFamily: 'var(--font-main)', fontSize: '16px' }}>
            No traffic data available for this time range.
          </div>
        )
      )}
    </div>
  )
}

export default LiveTraffic