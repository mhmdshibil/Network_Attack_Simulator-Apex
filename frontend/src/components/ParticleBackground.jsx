import React, { useEffect, useRef } from 'react'

const PARTICLE_COUNT = 220
const FLARE_LIFETIME = 1400
const RING_LIFETIME  = 1800

function rand(min, max) { return min + Math.random() * (max - min) }

export default function ParticleBackground() {
  const canvasRef = useRef(null)
  const stateRef  = useRef({ particles: [], flares: [], rings: [], raf: null, lastNow: 0 })

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const canvas  = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    function resize() {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Init slow-drifting white dots
    const W = canvas.width, H = canvas.height
    stateRef.current.particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x:     rand(0, W),
      y:     rand(0, H),
      vx:    rand(-0.12, 0.12),
      vy:    rand(-0.12, 0.12),
      r:     rand(0.4, 1.4),
      alpha: rand(0.10, 0.38),
    }))

    if (reduced) {
      // Static snapshot — draw once, no animation
      ctx.fillStyle = '#000'
      ctx.fillRect(0, 0, W, H)
      stateRef.current.particles.forEach(p => {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${p.alpha})`
        ctx.fill()
      })
      return () => window.removeEventListener('resize', resize)
    }

    function spawnFlare(detail) {
      const label      = detail?.label || detail?.attack_type || ''
      if (label === 'normal') return
      const confidence = typeof detail?.confidence === 'number' ? detail.confidence : 0.7
      const score      = typeof detail?.risk_score === 'number'  ? detail.risk_score  : 50
      // Intensity: driven by confidence + risk_score, no hue
      const intensity  = Math.min(0.4 + confidence * 0.4 + (score / 100) * 0.2, 1.0)
      const size       = 6 + intensity * 18
      const x = rand(canvas.width  * 0.08, canvas.width  * 0.92)
      const y = rand(canvas.height * 0.08, canvas.height * 0.92)
      const born = performance.now()
      stateRef.current.flares.push({ x, y, size, intensity, born })
      stateRef.current.rings.push({  x, y, maxR: 50 + size * 5, intensity, born })
    }

    function update(dt) {
      const W = canvas.width, H = canvas.height
      stateRef.current.particles.forEach(p => {
        p.x += p.vx * dt * 0.06
        p.y += p.vy * dt * 0.06
        if (p.x < -2)  p.x = W + 2
        if (p.x > W+2) p.x = -2
        if (p.y < -2)  p.y = H + 2
        if (p.y > H+2) p.y = -2
      })
    }

    function draw(now) {
      const W = canvas.width, H = canvas.height
      // Pure black background
      ctx.fillStyle = '#000000'
      ctx.fillRect(0, 0, W, H)

      // Drifting dots
      stateRef.current.particles.forEach(p => {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${p.alpha})`
        ctx.fill()
      })

      // Detection flares (bright radial glow)
      stateRef.current.flares = stateRef.current.flares.filter(f => {
        const age = now - f.born
        if (age > FLARE_LIFETIME) return false
        const t     = age / FLARE_LIFETIME
        const alpha = (1 - t) * f.intensity
        const r     = f.size * (1 + t * 2.5)
        const g     = ctx.createRadialGradient(f.x, f.y, 0, f.x, f.y, r)
        g.addColorStop(0,   `rgba(255,255,255,${alpha})`)
        g.addColorStop(0.4, `rgba(255,255,255,${alpha * 0.4})`)
        g.addColorStop(1,   'rgba(255,255,255,0)')
        ctx.beginPath()
        ctx.arc(f.x, f.y, r, 0, Math.PI * 2)
        ctx.fillStyle = g
        ctx.fill()
        return true
      })

      // Expanding rings
      stateRef.current.rings = stateRef.current.rings.filter(r => {
        const age = now - r.born
        if (age > RING_LIFETIME) return false
        const t       = age / RING_LIFETIME
        const radius  = r.maxR * t
        const alpha   = (1 - t) * 0.75 * r.intensity
        const lw      = 1.5 * (1 - t * 0.7)
        ctx.beginPath()
        ctx.arc(r.x, r.y, radius, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(255,255,255,${alpha})`
        ctx.lineWidth   = lw
        ctx.stroke()
        return true
      })
    }

    function frame(now) {
      const dt = Math.min(now - stateRef.current.lastNow, 40)
      stateRef.current.lastNow = now
      update(dt)
      draw(now)
      stateRef.current.raf = requestAnimationFrame(frame)
    }
    stateRef.current.raf = requestAnimationFrame(frame)

    // Subscribe to real detection events dispatched by useDetectionStream
    function onDetection(evt) { spawnFlare(evt.detail) }
    window.addEventListener('apex:detection', onDetection)

    return () => {
      window.removeEventListener('resize', resize)
      window.removeEventListener('apex:detection', onDetection)
      if (stateRef.current.raf) cancelAnimationFrame(stateRef.current.raf)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0, pointerEvents: 'none' }}
    />
  )
}
