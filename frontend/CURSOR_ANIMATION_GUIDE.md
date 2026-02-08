# Cursor Energy Field - Integration Guide

## ✅ Installation Complete

The cursor energy field has been safely integrated into your app as a passive visual enhancement layer.

**Zero breaking changes** - it runs behind everything with `pointer-events: none`.

---

## 🎨 Customization

All settings are in **`src/App.jsx`** in the `useEffect` hook:

```javascript
const energyField = new CursorEnergyField({
  // Particle density
  particleCount: 140,           // More = denser field
  
  // Layer positioning
  zIndex: -1,                   // -1 = behind content, 999 = in front
  
  // Physics behavior
  cursorInfluenceRadius: 200,   // How far cursor affects particles
  attractionStrength: 0.0008,   // Pull toward cursor
  orbitalStrength: 0.00035,     // Circular motion strength
  damping: 0.94,                // 0.9-0.98 (lower = slower)
  cohesionStrength: 0.00015,    // Particle grouping
  
  // Visual style
  opacity: 0.6,                 // 0-1 overall brightness
  particleSize: 2.5,            // Base dot size
  glowStrength: 12,             // Glow radius multiplier
  
  // Color palette (RGB values)
  colors: [
    { r: 100, g: 220, b: 255 }, // Cyan
    { r: 180, g: 120, b: 255 }, // Violet
    { r: 255, g: 100, b: 200 }, // Magenta
  ],
})
```

---

## 🎯 Common Adjustments

### Make it more subtle
```javascript
particleCount: 80,
opacity: 0.4,
attractionStrength: 0.0005,
```

### Make it more intense
```javascript
particleCount: 200,
opacity: 0.8,
cursorInfluenceRadius: 300,
attractionStrength: 0.0012,
```

### Change colors to match brand
```javascript
colors: [
  { r: 255, g: 100, b: 50 },  // Orange
  { r: 255, g: 200, b: 50 },  // Yellow
]
```

### Disable on mobile (performance)
```javascript
if (window.innerWidth > 768) {
  const energyField = new CursorEnergyField({ ... })
}
```

---

## 🔧 API Methods

```javascript
// Store reference to control it later
const [energyField, setEnergyField] = useState(null)

useEffect(() => {
  const field = new CursorEnergyField({ ... })
  setEnergyField(field)
  return () => field.destroy()
}, [])

// Then use these methods:
energyField.pause()                    // Stop animation
energyField.resume()                   // Resume animation
energyField.updateConfig({ opacity: 0.3 })  // Change settings live
energyField.destroy()                  // Remove completely
```

---

## 🚀 Performance

- Auto-scales particle count based on screen size
- Pauses when tab is inactive
- Target 60fps on modern devices
- Uses efficient force calculations

If you notice lag:
- Reduce `particleCount` to 80-100
- Increase `damping` to 0.96
- Lower `glowStrength` to 8

---

## 🛠️ Technical Details

- **Zero layout interference** - fixed position canvas overlay  
- **No pointer blocking** - `pointer-events: none`  
- **No scroll conflicts** - completely independent layer  
- **Auto cleanup** - destroys on unmount  
- **Mobile friendly** - auto-scales based on screen size  

The animation uses force-based physics:
- Cursor attraction (gravity-like pull)
- Orbital motion (tangential force)
- Cohesion (flocking behavior)
- Damping (viscosity/friction)
- Ambient drift (organic micro-motion)

---

## ❌ Remove Completely

In `src/App.jsx`, delete:

1. The import: `import CursorEnergyField from './components/CursorEnergyField'`
2. The entire `useEffect` block

---

## 💡 Tips

- The effect looks best with **darker backgrounds**
- Combine with your existing ParticleBackground for depth
- Try z-index: 1 to overlay content (but keep it subtle)
- Experiment with color palettes - monochrome works great too

---

**Questions?** The entire implementation is in `src/components/CursorEnergyField.js` - fully commented and customizable.
