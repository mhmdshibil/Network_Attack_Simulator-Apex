import React, { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import ParticleBackground from './components/ParticleBackground'
import UnifiedDashboard from './pages/UnifiedDashboard'
import CursorEnergyField from './components/CursorEnergyField'

function App() {
  const [activeSection, setActiveSection] = useState('dashboard')

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
      <div className="layout">
        <Sidebar activeSection={activeSection} setActiveSection={setActiveSection} />
        <div className="main-content">
          <main className="content">
            <UnifiedDashboard activeSection={activeSection} setActiveSection={setActiveSection} />
          </main>
        </div>
      </div>
    </>
  )
}

export default App
