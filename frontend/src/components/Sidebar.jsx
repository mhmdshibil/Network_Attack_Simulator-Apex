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

        {/* ── Brand ── */}
        <div className="navbar-brand">
          <svg width="30" height="30" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="16,2 30,28 2,28" fill="none" stroke="#4285f4" strokeWidth="2"/>
            <polygon points="16,9 25,26 7,26" fill="#4285f4" opacity="0.18"/>
            <line x1="16" y1="2" x2="16" y2="28" stroke="#4285f4" strokeWidth="1.2" opacity="0.5"/>
            <circle cx="16" cy="16" r="2.8" fill="#4285f4"/>
          </svg>
          <span className="navbar-title" style={{ letterSpacing: '0.03em' }}>
            Apex<span style={{ color: '#4285f4', fontWeight: 700 }}>-Kinetics</span>
          </span>
        </div>

        {/* ── Nav items ── */}
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