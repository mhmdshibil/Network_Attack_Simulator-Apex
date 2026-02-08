/**
 * CursorEnergyField - Premium cursor-reactive particle animation
 * 
 * A passive visual enhancement layer that creates an abstract particle field
 * with force-based physics. Particles orbit and flow around the cursor with
 * smooth, intelligent motion.
 * 
 * ZERO impact on existing layout, styles, or DOM structure.
 * 
 * @example
 * import CursorEnergyField from './CursorEnergyField'
 * 
 * const field = new CursorEnergyField({
 *   particleCount: 140,
 *   zIndex: -1
 * })
 */

class CursorEnergyField {
  constructor(config = {}) {
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // CONFIGURATION - Tweak these values
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    this.config = {
      particleCount: config.particleCount || 140,
      zIndex: config.zIndex !== undefined ? config.zIndex : -1,
      
      // Motion physics
      cursorInfluenceRadius: config.cursorInfluenceRadius || 220,
      attractionStrength: config.attractionStrength || 0.0008,
      orbitalStrength: config.orbitalStrength || 0.00035,
      damping: config.damping || 0.94,
      cohesionRadius: config.cohesionRadius || 180,
      cohesionStrength: config.cohesionStrength || 0.00015,
      driftSpeed: config.driftSpeed || 0.3,
      
      // Visual style
      colors: config.colors || [
        { r: 100, g: 220, b: 255 }, // cyan
        { r: 180, g: 120, b: 255 }, // violet
        { r: 255, g: 100, b: 200 }, // magenta
      ],
      particleSize: config.particleSize || 2.5,
      glowStrength: config.glowStrength || 12,
      opacity: config.opacity || 0.7,
      
      // Performance
      autoScaleParticles: config.autoScaleParticles !== false,
    }

    // State
    this.canvas = null
    this.ctx = null
    this.particles = []
    this.cursor = { x: window.innerWidth / 2, y: window.innerHeight / 2 }
    this.isActive = true
    this.animationFrameId = null

    // Initialize
    this._init()
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // INITIALIZATION
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  _init() {
    this._createCanvas()
    this._createParticles()
    this._setupEventListeners()
    this._startAnimation()
  }

  _createCanvas() {
    this.canvas = document.createElement('canvas')
    this.canvas.id = 'cursor-energy-field'
    
    // Critical styling - passive overlay, no interference
    Object.assign(this.canvas.style, {
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100vw',
      height: '100vh',
      pointerEvents: 'none',
      zIndex: this.config.zIndex.toString(),
      opacity: '1',
    })

    this.ctx = this.canvas.getContext('2d', { alpha: true })
    this._resize()
    
    // Mount to body
    document.body.appendChild(this.canvas)
  }

  _createParticles() {
    this.particles = []
    
    // Create grid of binary digits
    const gridSpacing = 30 // Distance between characters in grid
    const cols = Math.ceil(window.innerWidth / gridSpacing)
    const rows = Math.ceil(window.innerHeight / gridSpacing)

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const digit = Math.random() > 0.5 ? '1' : '0'
        
        // Check for dark mode (explicit class takes precedence over media query)
        const hasLightClass = document.documentElement.classList.contains('light-mode')
        const hasDarkClass = document.documentElement.classList.contains('dark-mode')
        
        let isDarkMode
        if (hasLightClass) {
          isDarkMode = false
        } else if (hasDarkClass) {
          isDarkMode = true
        } else {
          // Fall back to media query
          isDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
        }
        
        const particle = {
          // Position - fixed grid positions
          x: col * gridSpacing + gridSpacing / 2,
          y: row * gridSpacing + gridSpacing / 2,
          
          // Original position (for returning to)
          originX: col * gridSpacing + gridSpacing / 2,
          originY: row * gridSpacing + gridSpacing / 2,
          
          // Velocity
          vx: 0,
          vy: 0,
          
          // Physics properties
          mass: 1,
          
          // Visual properties - highly vivid neon colors for dark mode, standard for light
          digit: digit,
          color: digit === '1' 
            ? (isDarkMode ? { r: 255, g: 40, b: 80 } : { r: 255, g: 50, b: 50 }) 
            : (isDarkMode ? { r: 40, g: 200, b: 255 } : { r: 50, g: 150, b: 255 }),
          opacity: 0, // Start invisible
          targetOpacity: 0,
        }

        this.particles.push(particle)
      }
    }
    
    console.log(`Created grid: ${cols}x${rows} = ${this.particles.length} binary digits`)
  }

  _getParticleCount() {
    if (!this.config.autoScaleParticles) {
      return this.config.particleCount
    }

    // Scale particle count based on screen size
    const area = window.innerWidth * window.innerHeight
    const baseArea = 1920 * 1080
    const scale = Math.sqrt(area / baseArea)
    
    return Math.floor(this.config.particleCount * Math.min(scale, 1.5))
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // EVENT LISTENERS
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  _setupEventListeners() {
    // Track cursor position
    this._onMouseMove = (e) => {
      this.cursor.x = e.clientX
      this.cursor.y = e.clientY
    }
    window.addEventListener('mousemove', this._onMouseMove, { passive: true })

    // Handle resize
    this._onResize = () => this._resize()
    window.addEventListener('resize', this._onResize, { passive: true })

    // Pause when tab is inactive (performance)
    this._onVisibilityChange = () => {
      this.isActive = !document.hidden
      if (this.isActive && !this.animationFrameId) {
        this._startAnimation()
      }
    }
    document.addEventListener('visibilitychange', this._onVisibilityChange)
    
    // Listen for dark mode changes (both class and media query)
    this._onDarkModeChange = () => {
      // Recreate particles with updated colors
      this._createParticles()
    }
    
    // Watch for dark-mode class changes using MutationObserver
    this._darkModeObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          this._onDarkModeChange()
        }
      })
    })
    this._darkModeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    })
    
    // Also listen to media query changes
    if (window.matchMedia) {
      this._darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)')
      this._darkModeQuery.addEventListener('change', this._onDarkModeChange)
    }
  }

  _resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2) // Limit for performance
    this.canvas.width = window.innerWidth * dpr
    this.canvas.height = window.innerHeight * dpr
    this.canvas.style.width = `${window.innerWidth}px`
    this.canvas.style.height = `${window.innerHeight}px`
    this.ctx.scale(dpr, dpr)
    
    // Recreate grid when window resizes
    this._createParticles()
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // PHYSICS ENGINE - Force-based motion
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  _updatePhysics() {
    const cursorRadius = this.config.cursorInfluenceRadius
    const visibilityRadius = 150 // Particles only visible within this radius
    let particlesAffected = 0

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i]

      // Calculate distance to cursor
      const dx = this.cursor.x - p.x
      const dy = this.cursor.y - p.y
      const distSq = dx * dx + dy * dy
      const dist = Math.sqrt(distSq)

      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // VISIBILITY: Fade in when cursor is near
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      if (dist < visibilityRadius) {
        // Fade in smoothly based on distance
        const fadeStrength = 1 - (dist / visibilityRadius)
        p.targetOpacity = fadeStrength * this.config.opacity
      } else {
        p.targetOpacity = 0
      }
      
      // Smooth opacity transition
      p.opacity += (p.targetOpacity - p.opacity) * 0.1

      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // FORCE 1: Cursor REPULSION (push away like balloon displacement)
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      if (dist < cursorRadius && dist > 0.1) {
        particlesAffected++
        // Stronger push when closer (inverse square for realistic displacement)
        const repulsionStrength = this.config.attractionStrength * Math.pow((1 - dist / cursorRadius), 2)
        // Push AWAY from cursor (negative direction)
        p.vx -= (dx / dist) * repulsionStrength * (1 / p.mass)
        p.vy -= (dy / dist) * repulsionStrength * (1 / p.mass)
      }

      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // FORCE 2: Flow around cursor (tangential force for smooth displacement)
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      if (dist < cursorRadius && dist > 10) {
        const flowForce = this.config.orbitalStrength * (1 - dist / cursorRadius)
        // Perpendicular vector makes particles flow around like water
        p.vx += -dy / dist * flowForce
        p.vy += dx / dist * flowForce
      }

      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // FORCE 3: Return to origin (elastic snap back to grid position)
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      const returnStrength = 0.01
      const dxOrigin = p.originX - p.x
      const dyOrigin = p.originY - p.y
      p.vx += dxOrigin * returnStrength
      p.vy += dyOrigin * returnStrength

      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      // Apply damping (viscosity)
      // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      p.vx *= this.config.damping
      p.vy *= this.config.damping

      // Update position
      p.x += p.vx
      p.y += p.vy
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // RENDERING - Premium glow effect
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  _render() {
    // Clear canvas with transparency
    this.ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)

    // Setup text rendering
    this.ctx.font = 'bold 16px monospace'
    this.ctx.textAlign = 'center'
    this.ctx.textBaseline = 'middle'

    for (const p of this.particles) {
      // Skip invisible particles for performance
      if (p.opacity < 0.01) continue
      
      const { r, g, b } = p.color
      this.ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${p.opacity})`
      
      // Draw the binary digit
      this.ctx.fillText(p.digit, p.x, p.y)
    }
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // ANIMATION LOOP
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  _startAnimation() {
    const animate = () => {
      if (!this.isActive) {
        this.animationFrameId = null
        return
      }

      this._updatePhysics()
      this._render()

      this.animationFrameId = requestAnimationFrame(animate)
    }

    animate()
  }

  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  // PUBLIC API
  // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /**
   * Update configuration on the fly
   */
  updateConfig(newConfig) {
    Object.assign(this.config, newConfig)
    
    // Recreate particles if count changed
    if (newConfig.particleCount) {
      this._createParticles()
    }
  }

  /**
   * Pause animation
   */
  pause() {
    this.isActive = false
  }

  /**
   * Resume animation
   */
  resume() {
    if (!this.isActive) {
      this.isActive = true
      this._startAnimation()
    }
  }

  /**
   * Clean up and destroy
   */
  destroy() {
    this.isActive = false
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId)
    }

    window.removeEventListener('mousemove', this._onMouseMove)
    window.removeEventListener('resize', this._onResize)
    document.removeEventListener('visibilitychange', this._onVisibilityChange)
    
    // Clean up dark mode listeners
    if (this._darkModeObserver) {
      this._darkModeObserver.disconnect()
    }
    
    if (this._darkModeQuery && this._onDarkModeChange) {
      this._darkModeQuery.removeEventListener('change', this._onDarkModeChange)
    }

    if (this.canvas && this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas)
    }

    this.canvas = null
    this.ctx = null
    this.particles = []
  }
}

export default CursorEnergyField
