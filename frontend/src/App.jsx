import React, { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ParticleBackground from './components/ParticleBackground'
import UnifiedDashboard from './pages/UnifiedDashboard'
import CursorEnergyField from './components/CursorEnergyField'
import LoginModal from './components/LoginModal'
import DemoPanel from './components/DemoPanel'
import NarrativeOverlay from './components/NarrativeOverlay'
import DemoLanding from './pages/DemoLanding'
import { AuthProvider, useAuth } from './context/AuthContext'
import { setUnauthorizedHandler, triggerDemoAttack, startScenario, stopScenario, resetDemo } from './api/api'
import { useDemoShortcuts, ShortcutsHelp } from './hooks/useDemoShortcuts.jsx'

// ── Reset confirmation modal (used by keyboard shortcut R + DemoPanel) ────────
function ResetModal({ onClose, onConfirm, resetting }) {
  const T = { bg: '#0a0a0a', border: 'rgba(255,255,255,0.12)', text: '#fff', muted: 'rgba(255,255,255,0.55)', red: 'rgba(220,50,50,0.85)', redBg: 'rgba(200,40,40,0.10)', redBorder: 'rgba(200,40,40,0.28)' }
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 600, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div onClick={e => e.stopPropagation()} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: '14px', padding: '24px 28px', maxWidth: '340px', boxShadow: '0 8px 40px rgba(0,0,0,0.9)', fontFamily: "'IBM Plex Mono',monospace" }}>
        <div style={{ fontSize: '13px', fontWeight: 700, color: T.text, marginBottom: '12px', fontFamily: "'Space Grotesk',sans-serif" }}>Reset Demo Data</div>
        <p style={{ fontSize: '11px', color: T.muted, lineHeight: '1.6', margin: '0 0 20px' }}>
          This will clear all detections, blocked IPs, and triage cases. Are you sure?
        </p>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={onClose} style={{ flex: 1, padding: '8px', background: 'rgba(255,255,255,0.06)', border: `1px solid ${T.border}`, borderRadius: '8px', color: T.muted, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', cursor: 'pointer' }}>
            Cancel
          </button>
          <button onClick={onConfirm} disabled={resetting} style={{ flex: 1, padding: '8px', background: T.redBg, border: `1px solid ${T.redBorder}`, borderRadius: '8px', color: T.red, fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 700, cursor: resetting ? 'not-allowed' : 'pointer', opacity: resetting ? 0.6 : 1 }}>
            {resetting ? 'Resetting…' : 'Reset'}
          </button>
        </div>
      </div>
    </div>
  )
}

function AppInner() {
  const [activeSection, setActiveSection] = useState('dashboard')
  const [showResetModal, setShowResetModal] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [resetToast, setResetToast] = useState(null)

  const { onUnauthorized, token, role, authRequired, demoMode, logout } = useAuth()
  const isAdmin = !authRequired || role === 'admin'

  useEffect(() => {
    setUnauthorizedHandler(onUnauthorized)
  }, [onUnauthorized])

  useEffect(() => {
    const energyField = new CursorEnergyField({
      zIndex: 1,
      cursorInfluenceRadius: 150,
      attractionStrength: 0.06,
      orbitalStrength: 0.03,
      damping: 0.88,
      opacity: 0.5,
    })
    return () => energyField.destroy()
  }, [])

  const handleConfirmReset = useCallback(async () => {
    setResetting(true)
    try {
      await resetDemo()
      setShowResetModal(false)
      setResetToast('System reset — ready for demo')
      setTimeout(() => { window.location.reload() }, 2000)
    } catch (e) {
      setResetToast(e.message)
    } finally {
      setResetting(false)
    }
  }, [])

  const openReset = useCallback(() => {
    if (isAdmin) setShowResetModal(true)
  }, [isAdmin])

  // Keyboard shortcuts (active when demo mode is on)
  const { showHelp, closeHelp } = useDemoShortcuts({
    active: demoMode,
    onFire: () => triggerDemoAttack(null).catch(() => {}),
    onStartScenario: () => startScenario('corporate_breach').catch(() => {}),
    onStopScenario: () => stopScenario().catch(() => {}),
    onReset: openReset,
  })

  return (
    <>
      <ParticleBackground />
      <LoginModal />

      {demoMode && <DemoPanel onResetRequest={isAdmin ? openReset : null} />}
      <NarrativeOverlay />

      {showResetModal && (
        <ResetModal
          onClose={() => setShowResetModal(false)}
          onConfirm={handleConfirmReset}
          resetting={resetting}
        />
      )}

      {showHelp && <ShortcutsHelp onClose={closeHelp} />}

      {resetToast && (
        <div style={{
          position: 'fixed', bottom: '24px', left: '50%', transform: 'translateX(-50%)',
          zIndex: 700, background: '#0a0a0a', border: '1px solid rgba(255,255,255,0.18)',
          borderRadius: '10px', padding: '10px 20px',
          fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: '#fff',
          boxShadow: '0 4px 20px rgba(0,0,0,0.8)',
        }}>
          {resetToast}
        </div>
      )}

      <div className="layout">
        <Sidebar
          activeSection={activeSection}
          setActiveSection={setActiveSection}
          role={role}
          authRequired={authRequired}
          onLogout={logout}
        />
        <div className="main-content">
          <main className="content">
            <UnifiedDashboard activeSection={activeSection} setActiveSection={setActiveSection} />
          </main>
        </div>
      </div>
    </>
  )
}

function App() {
  // Serve the demo landing page at /demo (no auth, no sidebar — second-screen view)
  if (window.location.pathname === '/demo') {
    return <DemoLanding />
  }

  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  )
}

export default App
