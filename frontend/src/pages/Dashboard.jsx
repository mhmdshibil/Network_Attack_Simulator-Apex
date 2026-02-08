import React, { useRef, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { AlertCircle, Shield, AlertTriangle, Zap } from 'lucide-react'
import { usePolling } from '../hooks/usePolling'
import { useCursorPhysics } from '../hooks/useCursorPhysics'

function Dashboard() {
  const { data: healthData, error: healthError } = usePolling('http://127.0.0.1:8000/api/health')
  const { data: metricsData, error: metricsError } = usePolling('http://127.0.0.1:8000/api/metrics')
  const { data: timelineData, error: timelineError } = usePolling('http://127.0.0.1:8000/api/analytics/timeline')

  const { getInfluence } = useCursorPhysics()
  const cardRefs = useRef([])

  const isOffline = healthError || metricsError || timelineError

  // Format timeline data for chart
  const chartData = timelineData?.timeline || []

  // Apply physics influence to metric cards
  useEffect(() => {
    let frameId = null

    const applyPhysics = () => {
      cardRefs.current.forEach((ref) => {
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

  return (
    <div>
      {isOffline && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline - Check your API connection
        </div>
      )}

      <div className="metrics-grid">
        <div 
          ref={(el) => (cardRefs.current[0] = el)}
          className="metric-card health"
          style={{ transition: 'transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
        >
          <div className="metric-label">System Health</div>
          <div className="metric-value">
            {healthData?.status === 'healthy' ? 'Healthy' : healthData?.status || 'Unknown'}
          </div>
          <Shield size={40} className="metric-icon" />
          <div className="metric-subtext">
            {healthData?.last_checked ? `Updated: ${new Date(healthData.last_checked).toLocaleTimeString()}` : 'Loading...'}
          </div>
        </div>

        <div 
          ref={(el) => (cardRefs.current[1] = el)}
          className="metric-card detections"
          style={{ transition: 'transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
        >
          <div className="metric-label">Total Detections</div>
          <div className="metric-value">
            {metricsData?.total_detections || '0'}
          </div>
          <AlertTriangle size={40} className="metric-icon" />
          <div className="metric-subtext">All time</div>
        </div>

        <div 
          ref={(el) => (cardRefs.current[2] = el)}
          className="metric-card risky"
          style={{ transition: 'transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
        >
          <div className="metric-label">Active Risky IPs</div>
          <div className="metric-value">
            {metricsData?.active_risky_ips || '0'}
          </div>
          <AlertCircle size={40} className="metric-icon" />
          <div className="metric-subtext">Currently monitored</div>
        </div>

        <div 
          ref={(el) => (cardRefs.current[3] = el)}
          className="metric-card confidence"
          style={{ transition: 'transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
        >
          <div className="metric-label">Avg Confidence</div>
          <div className="metric-value">
            {metricsData?.average_confidence ? `${metricsData.average_confidence.toFixed(1)}%` : 'N/A'}
          </div>
          <Zap size={40} className="metric-icon" />
          <div className="metric-subtext">
            {metricsData?.last_detection ? `Last: ${new Date(metricsData.last_detection).toLocaleTimeString()}` : 'No detections'}
          </div>
        </div>
      </div>

      {chartData.length > 0 && (
        <div className="chart-container">
          <h3 className="chart-title">Traffic Timeline</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
              <XAxis dataKey="timestamp" stroke="var(--text-tertiary)" />
              <YAxis stroke="var(--text-tertiary)" />
              <Tooltip
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-medium)', borderRadius: '8px' }}
                labelStyle={{ color: 'var(--text-primary)' }}
              />
              <Line type="monotone" dataKey="packet_count" stroke="#4285f4" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

export default Dashboard

