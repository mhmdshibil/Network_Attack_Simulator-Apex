import React, { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { AlertCircle } from 'lucide-react'
import { usePolling } from '../hooks/usePolling'

function LiveTraffic() {
  const [timeRange, setTimeRange] = useState('1h')
  const { data: timelineData, error } = usePolling('http://127.0.0.1:8000/api/analytics/timeline?window=' + timeRange)

  const chartData = timelineData?.timeline || []

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
        <div>
          <h2 style={{ fontSize: '32px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px' }}>
            Live Traffic Monitor
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Real-time network activity visualization</p>
        </div>
        <div className="time-range-buttons">
          <button
            className={`time-btn ${timeRange === '5m' ? 'active' : ''}`}
            onClick={() => setTimeRange('5m')}
          >
            5 Minutes
          </button>
          <button
            className={`time-btn ${timeRange === '1h' ? 'active' : ''}`}
            onClick={() => setTimeRange('1h')}
          >
            1 Hour
          </button>
          <button
            className={`time-btn ${timeRange === '24h' ? 'active' : ''}`}
            onClick={() => setTimeRange('24h')}
          >
            24 Hours
          </button>
        </div>
      </div>

      {error && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline - Check your API connection
        </div>
      )}

      {chartData.length > 0 && (
        <div className="chart-container">
          <h3 className="chart-title">Traffic Over Time</h3>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
              <XAxis dataKey="timestamp" stroke="var(--text-tertiary)" />
              <YAxis stroke="var(--text-tertiary)" />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-medium)', borderRadius: '8px' }}
                labelStyle={{ color: 'var(--text-primary)' }}
              />
              <Legend />
              <Line type="monotone" dataKey="packet_count" stroke="#4285f4" dot={false} strokeWidth={2} name="Packets" />
              <Line type="monotone" dataKey="event_count" stroke="#ea4335" dot={false} strokeWidth={2} name="Events" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default LiveTraffic

