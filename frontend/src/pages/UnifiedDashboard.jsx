import React, { useState, useRef, useEffect } from 'react'
import Dashboard from './Dashboard'
import LiveTraffic from './LiveTraffic'
import DetectedAttacks from './DetectedAttacks'
import RiskAnalysis from './RiskAnalysis'
import AttackAnalytics from './AttackAnalytics'
import BlockedIPs from './BlockedIPs'
import { useCursorPhysics } from '../hooks/useCursorPhysics'

function UnifiedDashboard({ activeSection, setActiveSection }) {
  const { getInfluence } = useCursorPhysics()
  const sectionRefsRef = useRef({})

  // Apply physics influence to active section (subtle global effect)
  useEffect(() => {
    let frameId = null

    const applyPhysics = () => {
      const activeRef = sectionRefsRef.current[activeSection]
      if (!activeRef) return

      const rect = activeRef.getBoundingClientRect()
      const influence = getInfluence(rect, 200, 2) // Subtle influence on whole section

      activeRef.style.transform = `translate(${influence.x}px, ${influence.y}px)`
    }

    frameId = requestAnimationFrame(applyPhysics)
    return () => cancelAnimationFrame(frameId)
  }, [activeSection, getInfluence])

  const sections = {
    dashboard: { component: Dashboard, label: 'Dashboard' },
    'live-traffic': { component: LiveTraffic, label: 'Live Traffic' },
    'detected-attacks': { component: DetectedAttacks, label: 'Detected Attacks' },
    'risk-analysis': { component: RiskAnalysis, label: 'Risk Analysis' },
    'attack-analytics': { component: AttackAnalytics, label: 'Attack Analytics' },
    'blocked-ips': { component: BlockedIPs, label: 'Blocked IPs' },
  }

  return (
    <div className="unified-dashboard">
      {Object.entries(sections).map(([key, { component: Component }]) => {
        const isActive = activeSection === key

        return (
          <section
            key={key}
            ref={(el) => {
              sectionRefsRef.current[key] = el
            }}
            className={`dashboard-section ${isActive ? 'active' : 'inactive'}`}
            style={{
              opacity: isActive ? 1 : 0,
              pointerEvents: isActive ? 'auto' : 'none',
              transition: 'opacity 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
              transform: isActive ? 'translateX(0) scale(1)' : 'translateX(40px) scale(0.95)',
              willChange: 'opacity, transform',
            }}
          >
            <Component />
          </section>
        )
      })}
    </div>
  )
}

export default UnifiedDashboard
