/**
 * CursorEnergyField - Simple & Efficient
 *
 * Minimal white dot trail that follows the cursor and fades out.
 * No grid, no heavy physics — just a clean glowing trail.
 */

class CursorEnergyField {
  constructor(config = {}) {
    this.config = {
      zIndex:      config.zIndex !== undefined ? config.zIndex : 1,
      trailLength: config.trailLength || 18,
      dotSize:     config.dotSize    || 3,
      fadeSpeed:   config.fadeSpeed  || 0.08,
    }

    this.canvas   = null
    this.ctx      = null
    this.trail    = []
    this.isActive = true
    this.animationFrameId = null

    this._init()
  }

  _init() {
    this._createCanvas()
    this._setupEventListeners()
    this._startAnimation()
  }

  _createCanvas() {
    this.canvas = document.createElement('canvas')
    this.canvas.id = 'cursor-energy-field'

    Object.assign(this.canvas.style, {
      position:      'fixed',
      top:           '0',
      left:          '0',
      width:         '100vw',
      height:        '100vh',
      pointerEvents: 'none',
      zIndex:        this.config.zIndex.toString(),
    })

    this.ctx = this.canvas.getContext('2d', { alpha: true })
    this._resize()
    document.body.appendChild(this.canvas)
  }

  _setupEventListeners() {
    this._onMouseMove = (e) => {
      this.trail.push({ x: e.clientX, y: e.clientY, opacity: 0.75 })
      if (this.trail.length > this.config.trailLength) this.trail.shift()
    }
    window.addEventListener('mousemove', this._onMouseMove, { passive: true })

    this._onResize = () => this._resize()
    window.addEventListener('resize', this._onResize, { passive: true })

    this._onVisibilityChange = () => {
      this.isActive = !document.hidden
      if (this.isActive && !this.animationFrameId) this._startAnimation()
    }
    document.addEventListener('visibilitychange', this._onVisibilityChange)
  }

  _resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    this.canvas.width  = window.innerWidth  * dpr
    this.canvas.height = window.innerHeight * dpr
    this.canvas.style.width  = `${window.innerWidth}px`
    this.canvas.style.height = `${window.innerHeight}px`
    this.ctx.scale(dpr, dpr)
  }

  _update() {
    for (let i = this.trail.length - 1; i >= 0; i--) {
      this.trail[i].opacity -= this.config.fadeSpeed
      if (this.trail[i].opacity <= 0) this.trail.splice(i, 1)
    }
  }

  _render() {
    this.ctx.clearRect(0, 0, window.innerWidth, window.innerHeight)

    const total = this.trail.length
    for (let i = 0; i < total; i++) {
      const dot    = this.trail[i]
      if (dot.opacity <= 0) continue

      const scale  = (i + 1) / total
      const radius = this.config.dotSize * scale

      // Soft glow halo
      const grd = this.ctx.createRadialGradient(dot.x, dot.y, 0, dot.x, dot.y, radius * 3)
      grd.addColorStop(0,   `rgba(255, 255, 255, ${dot.opacity})`)
      grd.addColorStop(0.5, `rgba(210, 228, 255, ${dot.opacity * 0.4})`)
      grd.addColorStop(1,   'rgba(255, 255, 255, 0)')

      this.ctx.beginPath()
      this.ctx.arc(dot.x, dot.y, radius * 3, 0, Math.PI * 2)
      this.ctx.fillStyle = grd
      this.ctx.fill()

      // Crisp white core
      this.ctx.beginPath()
      this.ctx.arc(dot.x, dot.y, radius, 0, Math.PI * 2)
      this.ctx.fillStyle = `rgba(255, 255, 255, ${dot.opacity})`
      this.ctx.fill()
    }
  }

  _startAnimation() {
    const animate = () => {
      if (!this.isActive) { this.animationFrameId = null; return }
      this._update()
      this._render()
      this.animationFrameId = requestAnimationFrame(animate)
    }
    animate()
  }

  updateConfig(newConfig) { Object.assign(this.config, newConfig) }
  pause()  { this.isActive = false }
  resume() { if (!this.isActive) { this.isActive = true; this._startAnimation() } }

  destroy() {
    this.isActive = false
    if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId)
    window.removeEventListener('mousemove', this._onMouseMove)
    window.removeEventListener('resize',    this._onResize)
    document.removeEventListener('visibilitychange', this._onVisibilityChange)
    if (this.canvas?.parentNode) this.canvas.parentNode.removeChild(this.canvas)
    this.canvas = null
    this.ctx    = null
    this.trail  = []
  }
}

export default CursorEnergyField