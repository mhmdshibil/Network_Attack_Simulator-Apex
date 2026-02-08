import React, { useEffect, useState } from 'react'
import './CursorTrail.css'

function CursorTrail() {
  const [trails, setTrails] = useState([])
  const [radarSweep, setRadarSweep] = useState([])
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  useEffect(() => {
    let frameId = null
    let lastUpdate = 0
    let radarCounter = 0

    const handleMouseMove = (e) => {
      const now = Date.now()
      
      // Update trails every 30ms
      if (now - lastUpdate < 30) return
      lastUpdate = now

      const newMousePos = { x: e.clientX, y: e.clientY }
      setMousePos(newMousePos)

      // ANIMATION: Generate 8 binary digits in a circle around cursor
      const newTrails = []
      const count = 8
      const radius = 40 + Math.random() * 20

      for (let i = 0; i < count; i++) {
        const angle = (i / count) * Math.PI * 2 + Math.random() * 0.5
        const x = newMousePos.x + Math.cos(angle) * radius
        const y = newMousePos.y + Math.sin(angle) * radius
        const digit = Math.random() > 0.5 ? '1' : '0'
        const id = `${Date.now()}-${i}-${Math.random()}`

        newTrails.push({
          id,
          x,
          y,
          digit,
          createdAt: now,
        })
      }

      // ANIMATION: Add radar sweep pulse occasionally
      radarCounter++
      if (radarCounter % 3 === 0) {
        const radarId = `radar-${Date.now()}-${Math.random()}`
        setRadarSweep((prev) => {
          const updated = prev.filter((r) => now - r.createdAt < 800)
          return [
            ...updated,
            {
              id: radarId,
              x: newMousePos.x,
              y: newMousePos.y,
              createdAt: now,
            },
          ]
        })
      }

      setTrails((prev) => {
        const filtered = prev.filter((trail) => now - trail.createdAt < 1000)
        return [...filtered, ...newTrails]
      })
    }

    window.addEventListener('mousemove', handleMouseMove)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      if (frameId) cancelAnimationFrame(frameId)
    }
  }, [])

  return (
    <div className="cursor-trail-container">
      {/* ANIMATION: Radar sweep effect */}
      {radarSweep.map((sweep) => {
        const age = Date.now() - sweep.createdAt
        const scale = 1 + age / 200
        const opacity = 1 - age / 800

        return (
          <div
            key={sweep.id}
            className="radar-pulse"
            style={{
              left: `${sweep.x}px`,
              top: `${sweep.y}px`,
              opacity,
              transform: `translate(-50%, -50%) scale(${scale})`,
            }}
          />
        )
      })}

      {/* ANIMATION: Binary digit trail */}
      {trails.map((trail) => {
        const age = Date.now() - trail.createdAt
        const opacity = 1 - age / 1000
        const scale = 1 + age / 500

        return (
          <div
            key={trail.id}
            className="cursor-digit"
            style={{
              left: `${trail.x}px`,
              top: `${trail.y}px`,
              opacity,
              transform: `translate(-50%, -50%) scale(${scale})`,
            }}
          >
            {trail.digit}
          </div>
        )
      })}
    </div>
  )
}

export default CursorTrail
