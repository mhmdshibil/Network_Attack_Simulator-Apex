import React, { useRef, useEffect } from 'react'
import { Radio, Activity, AlertTriangle, TrendingUp, BarChart3, Lock, Sun, Moon } from 'lucide-react'
import { useCursorPhysics } from '../hooks/useCursorPhysics'
import { useDarkMode } from '../hooks/useDarkMode'

function Sidebar({ activeSection, setActiveSection }) {
  const { getInfluence } = useCursorPhysics()
  const { isDark, toggle } = useDarkMode()
  const navItemsRef = useRef([])

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'live-traffic', label: 'Live Traffic', icon: Activity },
    { id: 'detected-attacks', label: 'Attacks', icon: AlertTriangle },
    { id: 'risk-analysis', label: 'Risk Analysis', icon: TrendingUp },
    { id: 'attack-analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'blocked-ips', label: 'Blocked IPs', icon: Lock },
  ]

  // Apply physics influence to nav items
  useEffect(() => {
    let frameId = null

    const applyPhysics = () => {
      navItemsRef.current.forEach((ref) => {
        if (!ref) return

        const rect = ref.getBoundingClientRect()
        const influence = getInfluence(rect, 150, 2)

        ref.style.transform = `translate(${influence.x}px, ${influence.y}px)`
      })

      frameId = requestAnimationFrame(applyPhysics)
    }

    frameId = requestAnimationFrame(applyPhysics)
    return () => cancelAnimationFrame(frameId)
  }, [getInfluence])

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <Radio size={28} className="navbar-icon" />
          <span className="navbar-title">Network Attack</span>
        </div>

        <div className="navbar-menu">
          {menuItems.map((item, idx) => {
            const Icon = item.icon
            const isActive = activeSection === item.id

            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                ref={(el) => {
                  navItemsRef.current[idx] = el
                }}
                className={`nav-button ${isActive ? 'active' : ''}`}
                style={{
                  transition: 'all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
                  willChange: 'transform',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Icon size={18} className="nav-icon" />
                <span className="nav-label">{item.label}</span>
              </button>
            )
          })}
        </div>

        <div className="navbar-status">
          <span className="status-indicator"></span>
          Active
        </div>

        <button 
          className="navbar-theme-toggle" 
          onClick={toggle}
          aria-label="Toggle dark mode"
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </nav>
  )
}

export default Sidebar
