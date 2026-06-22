import React, { useState, useEffect } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertCircle, Wifi } from 'lucide-react'
import { fetchTimeline } from '../api/api'

const T = {
  bg:      '#131316',
  border:  '#232328',
  text:    '#F2F3F5',
  muted:   '#6E7180',
  accent:  '#2DD9FF',
  danger:  '#FF3B5C',
}

const SOCTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: T.bg, border: `1px solid ${T.border}`, borderRadius: '2px',
      padding: '10px 14px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text,
    }}>
      <div style={{ color: T.muted, marginBottom: '6px', letterSpacing: '0.05em' }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, display: 'flex', justifyContent: 'space-between', gap: '20px', marginTop: '3px' }}>
          <span style={{ opacity: 0.6 }}>{p.name}</span><strong>{p.value}</strong>
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
          event_count: item.events,
        }))
        setData(mapped)
        setError(null)
      } catch (err) { setError(err.message) }
    }
    loadData()
    const iv = setInterval(loadData, 5000)
    return () => clearInterval(iv)
  }, [timeRange])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '4px' }}>
            Live Traffic Monitor
          </div>
          <div style={{ fontFamily: "'IBM Plex Sans',sans-serif", fontSize: '20px', fontWeight: 600, color: T.text, letterSpacing: '-0.01em' }}>
            Network Activity
          </div>
        </div>
        <div className="time-range-buttons">
          {['5m', '1h', '24h'].map(r => (
            <button key={r} className={`time-btn ${timeRange === r ? 'active' : ''}`} onClick={() => setTimeRange(r)}>
              {r}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="demo-banner"><AlertCircle size={13} /> Backend offline — check API connection</div>
      )}

      {data.length > 0 ? (
        <div className="chart-container">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Wifi size={12} style={{ color: T.muted }} />
            <span className="chart-title" style={{ margin: 0 }}>Traffic over time</span>
            <span style={{ marginLeft: 'auto', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.accent, letterSpacing: '0.06em' }}>
              LIVE · {timeRange.toUpperCase()}
            </span>
          </div>

          <ResponsiveContainer width="100%" height={340}>
            <AreaChart data={data} margin={{ top: 4, right: 4, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="gPktsLT" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={T.accent} className="breathe-stop" />
                  <stop offset="95%" stopColor={T.accent} stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gEvtsLT" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={T.danger} stopOpacity={0.14}/>
                  <stop offset="95%" stopColor={T.danger} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: T.muted, fontFamily: "'IBM Plex Mono'" }} axisLine={{ stroke: T.border }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: "'IBM Plex Mono'" }} axisLine={false} tickLine={false} width={32} />
              <Tooltip content={<SOCTooltip />} />
              <Area type="monotone" dataKey="packet_count" stroke={T.accent} strokeWidth={1.5} fill="url(#gPktsLT)" dot={false} name="Packets" />
              <Area type="monotone" dataKey="event_count"  stroke={T.danger} strokeWidth={1}   fill="url(#gEvtsLT)" dot={false} name="Events" />
            </AreaChart>
          </ResponsiveContainer>

          <div style={{ display: 'flex', gap: '20px', marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${T.border}` }}>
            {[{ c: T.accent, l: 'Packets' }, { c: T.danger, l: 'Events' }].map((x, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontFamily: "'IBM Plex Mono'", fontSize: '10px', color: T.muted }}>
                <div style={{ width: '18px', height: '2px', background: x.c }} />
                {x.l}
              </div>
            ))}
          </div>
        </div>
      ) : (
        !error && (
          <div className="chart-container" style={{ textAlign: 'center', padding: '60px 20px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '12px', color: T.muted }}>
            no data for {timeRange} window
          </div>
        )
      )}
    </div>
  )
}

export default LiveTraffic
