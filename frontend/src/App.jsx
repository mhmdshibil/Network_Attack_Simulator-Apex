import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ParticleBackground from './components/ParticleBackground'
import UnifiedDashboard from './pages/UnifiedDashboard'
import CursorEnergyField from './components/CursorEnergyField'
import LoginModal from './components/LoginModal'
import { AuthProvider, useAuth } from './context/AuthContext'
import { setUnauthorizedHandler } from './api/api'

function AppInner() {
  const [activeSection, setActiveSection] = useState('dashboard')
  const { onUnauthorized, token, role, authRequired, logout } = useAuth()

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

  return (
    <>
      <ParticleBackground />
      <LoginModal />
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
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  )
}

export default App
