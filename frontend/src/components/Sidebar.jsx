import React, { useRef, useEffect } from 'react'
import { Activity, AlertTriangle, BarChart3, Lock, Sun, Moon, Wifi } from 'lucide-react'
import { useCursorPhysics } from '../hooks/useCursorPhysics'
import { useDarkMode } from '../hooks/useDarkMode'

function Sidebar({ activeSection, setActiveSection }) {
  const { getInfluence } = useCursorPhysics()
  const { isDark, toggle } = useDarkMode()
  const navItemsRef = useRef([])

  const menuItems = [
    { id: 'dashboard',        label: 'Dashboard',    icon: Activity },
    { id: 'live-traffic',     label: 'Live Traffic', icon: Wifi },
    { id: 'detected-attacks', label: 'Attacks',      icon: AlertTriangle },
    { id: 'attack-analytics', label: 'Analytics',    icon: BarChart3 },
    { id: 'blocked-ips',      label: 'Blocked IPs',  icon: Lock },
  ]

  useEffect(() => {
    let frameId = null
    const applyPhysics = () => {
      navItemsRef.current.forEach((ref) => {
        if (!ref) return
        const rect = ref.getBoundingClientRect()
        const influence = getInfluence(rect, 120, 1.5)
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

        {/* Brand */}
        <div className="navbar-brand">
          <svg width="20" height="20" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="16,3 29,27 3,27" fill="none" stroke="#2DD9FF" strokeWidth="1.5"/>
            <polygon points="16,10 24,25 8,25" fill="#2DD9FF" opacity="0.12"/>
            <line x1="16" y1="3" x2="16" y2="27" stroke="#2DD9FF" strokeWidth="1" opacity="0.4"/>
            <circle cx="16" cy="16" r="2.2" fill="#2DD9FF"/>
          </svg>
          <span className="navbar-title">Apex<span style={{ color: '#2DD9FF' }}>·K</span></span>
        </div>

        {/* Nav items */}
        <div className="navbar-menu">
          {menuItems.map((item, idx) => {
            const Icon = item.icon
            const isActive = activeSection === item.id
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                ref={(el) => { navItemsRef.current[idx] = el }}
                className={`nav-button ${isActive ? 'active' : ''}`}
                style={{ willChange: 'transform' }}
              >
                <Icon size={14} className="nav-icon" />
                <span className="nav-label">{item.label}</span>
              </button>
            )
          })}
        </div>

        {/* Footer: status + theme toggle */}
        <div className="sidebar-footer">
          <div className="navbar-status">
            <span className="status-indicator" />
            LIVE
          </div>
          <button
            className="navbar-theme-toggle"
            onClick={toggle}
            aria-label="Toggle dark mode"
            title={isDark ? 'Light mode' : 'Dark mode'}
          >
            {isDark ? <Sun size={12} /> : <Moon size={12} />}
          </button>
        </div>

      </div>
    </nav>
  )
}

export default Sidebar
