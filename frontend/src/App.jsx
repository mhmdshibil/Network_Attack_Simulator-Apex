import React, { useState, useEffect } from 'react'
import { Radio } from 'lucide-react'
import Sidebar from './components/Sidebar'
import ParticleBackground from './components/ParticleBackground'
import UnifiedDashboard from './pages/UnifiedDashboard'
import CursorEnergyField from './components/CursorEnergyField'

function App() {
  const [activeSection, setActiveSection] = useState('dashboard')

  // Initialize cursor energy field
  useEffect(() => {
    const energyField = new CursorEnergyField({
      zIndex: 1,
      cursorInfluenceRadius: 150,
      attractionStrength: 0.08,  // Repulsion force
      orbitalStrength: 0.04,     // Flow around effect
      damping: 0.85,
      opacity: 1.0,
    })

    // Cleanup on unmount
    return () => {
      energyField.destroy()
    }
  }, [])

  return (
    <>
      <ParticleBackground />
      <button className="floating-share-btn">Share</button>
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
