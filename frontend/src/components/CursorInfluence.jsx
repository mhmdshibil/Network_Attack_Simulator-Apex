import React, { useEffect, useRef, useState } from 'react'

/**
 * Component that renders cursor-driven floating elements
 * Creates visual feedback around cursor movement with physics-based motion
 */
function CursorInfluence() {
  const glowRef = useRef(null)
  const ringRef = useRef(null)
  const dotsContainerRef = useRef(null)
  const [particles, setParticles] = useState([])
  const cursorPosRef = useRef({ x: 0, y: 0 })

  useEffect(() => {
    let animationFrameId = null
    let lastParticleTime = 0

    const handleMouseMove = (e) => {
      cursorPosRef.current.x = e.clientX
      cursorPosRef.current.y = e.clientY

      // Update glow and ring directly without state (no delay!)
      if (glowRef.current) {
        glowRef.current.style.left = e.clientX + 'px'
        glowRef.current.style.top = e.clientY + 'px'
      }

      if (ringRef.current) {
        ringRef.current.style.left = e.clientX + 'px'
        ringRef.current.style.top = e.clientY + 'px'
      }

      // Particle spawning
      const now = Date.now()
      if (now - lastParticleTime > 50 && Math.random() > 0.7) {
        const angle = Math.random() * Math.PI * 2
        const distance = 30 + Math.random() * 40
        const particle = {
          id: Date.now() + Math.random(),
          x: e.clientX + Math.cos(angle) * distance,
          y: e.clientY + Math.sin(angle) * distance,
          vx: Math.cos(angle) * (Math.random() * 0.5 - 0.25),
          vy: Math.sin(angle) * (Math.random() * 0.5 - 0.25),
          life: 1,
          size: 2 + Math.random() * 3,
        }
        setParticles((prev) => [...prev.slice(-15), particle])
        lastParticleTime = now
      }
    }

    // Update orbiting dots in animation loop
    const updateDots = () => {
      if (dotsContainerRef.current) {
        const dots = dotsContainerRef.current.querySelectorAll('[data-dot]')
        dots.forEach((dot, idx) => {
          const angle = ((idx * 120) * Math.PI) / 180
          const orbitRadius = 50 + Math.sin(Date.now() * 0.003 + idx) * 15
          const x = cursorPosRef.current.x + Math.cos(angle) * orbitRadius
          const y = cursorPosRef.current.y + Math.sin(angle) * orbitRadius

          dot.style.left = x + 'px'
          dot.style.top = y + 'px'
        })
      }

      animationFrameId = requestAnimationFrame(updateDots)
    }

    window.addEventListener('mousemove', handleMouseMove)
    animationFrameId = requestAnimationFrame(updateDots)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  // Animate particles
  useEffect(() => {
    let frameId = null

    const animate = () => {
      setParticles((prev) =>
        prev
          .map((p) => ({
            ...p,
            x: p.x + p.vx,
            y: p.y + p.vy,
            vy: p.vy + 0.15, // gravity
            life: p.life - 0.02,
          }))
          .filter((p) => p.life > 0)
      )

      frameId = requestAnimationFrame(animate)
    }

    frameId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frameId)
  }, [])

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}>
      {/* Cursor glow effect - NO TRANSITION, direct DOM updates */}
      <div
        ref={glowRef}
        style={{
          position: 'fixed',
          width: '80px',
          height: '80px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(31, 113, 229, 0.1) 0%, rgba(31, 113, 229, 0) 70%)',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          filter: 'blur(20px)',
          opacity: 0.6,
          willChange: 'transform',
        }}
      />

      {/* Cursor ring - NO TRANSITION, direct DOM updates */}
      <div
        ref={ringRef}
        style={{
          position: 'fixed',
          width: '40px',
          height: '40px',
          border: '1px solid rgba(31, 113, 229, 0.3)',
          borderRadius: '50%',
          transform: 'translate(-50%, -50%)',
          pointerEvents: 'none',
          willChange: 'transform',
        }}
      />

      {/* Floating particles */}
      {particles.map((p) => (
        <div
          key={p.id}
          style={{
            position: 'fixed',
            left: p.x,
            top: p.y,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            background: `rgba(31, 113, 229, ${p.life * 0.4})`,
            transform: `translate(-50%, -50%)`,
            pointerEvents: 'none',
            boxShadow: `0 0 ${p.size * 2}px rgba(31, 113, 229, ${p.life * 0.3})`,
          }}
        />
      ))}

      {/* Secondary orbiting dots - direct DOM updates */}
      <div ref={dotsContainerRef}>
        {[0, 1, 2].map((idx) => (
          <div
            key={idx}
            data-dot={idx}
            style={{
              position: 'fixed',
              width: '4px',
              height: '4px',
              borderRadius: '50%',
              background: `rgba(66, 133, 244, ${0.5 - idx * 0.1})`,
              transform: 'translate(-50%, -50%)',
              pointerEvents: 'none',
              filter: 'blur(0.5px)',
              willChange: 'transform',
            }}
          />
        ))}
      </div>
    </div>
  )
}

export default CursorInfluence
