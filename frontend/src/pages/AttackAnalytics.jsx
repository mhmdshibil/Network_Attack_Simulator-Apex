import React, { useEffect, useState } from 'react'
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { AlertCircle } from 'lucide-react'
import { usePolling } from '../hooks/usePolling'

function AttackAnalytics() {
  const { data: trendsData, error: trendsError } = usePolling('http://127.0.0.1:8000/api/analytics/attack_trends')
  const { data: topAttackersData, error: topAttackersError } = usePolling('http://127.0.0.1:8000/api/analytics/top_attackers')
  const { data: timelineData, error: timelineError } = usePolling('http://127.0.0.1:8000/api/analytics/timeline')

  const attackTypeData = trendsData?.attack_trends || []
  const attacksOverTimeData = timelineData?.timeline || []
  const severityDistribution = topAttackersData?.severity_distribution || []

  const COLORS = ['#ea4335', '#fbbc04', '#34a853']
  const hasError = trendsError || topAttackersError || timelineError

  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <h2 style={{ fontSize: '32px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Attack Analytics
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Trends and insights from attack data</p>
      </div>

      {hasError && (
        <div className="demo-banner">
          <AlertCircle size={16} />
          Backend offline - Check your API connection
        </div>
      )}

      {attackTypeData.length > 0 && (
        <div className="chart-container">
          <h3 className="chart-title">Attack Type Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={attackTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
              <XAxis dataKey="name" stroke="var(--text-tertiary)" />
              <YAxis stroke="var(--text-tertiary)" />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-medium)', borderRadius: '8px' }}
                labelStyle={{ color: 'var(--text-primary)' }}
              />
              <Bar dataKey="value" fill="#fbbc04" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid-2">
        {attacksOverTimeData.length > 0 && (
          <div className="chart-container">
            <h3 className="chart-title">Attacks Over Time</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={attacksOverTimeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
                <XAxis dataKey="time" stroke="var(--text-tertiary)" />
                <YAxis stroke="var(--text-tertiary)" />
                <Tooltip 
                  contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-medium)', borderRadius: '8px' }}
                  labelStyle={{ color: 'var(--text-primary)' }}
                />
                <Line type="monotone" dataKey="count" stroke="#ea4335" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {severityDistribution.length > 0 && (
          <div className="chart-container">
            <h3 className="chart-title">Severity Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={severityDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {severityDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-medium)', borderRadius: '8px' }}
                  labelStyle={{ color: 'var(--text-primary)' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', marginTop: '16px', fontSize: '14px' }}>
              {severityDistribution.map((item, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '12px', height: '12px', background: COLORS[index % COLORS.length], borderRadius: '2px' }}></span>
                  <span>{item.name} {((item.value / severityDistribution.reduce((sum, x) => sum + x.value, 0)) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AttackAnalytics
