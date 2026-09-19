import { useState, useEffect, useCallback } from 'react'

/**
 * Keyboard shortcuts for live demos.
 * Only fires callbacks when `active` is true.
 *
 * Bindings (no modifier key required):
 *   D → trigger one random attack
 *   S → start scenario
 *   X → stop scenario
 *   R → open reset confirmation modal
 *   ? → toggle shortcuts help modal
 *   Escape → close help modal
 */
export function useDemoShortcuts({ active = false, onFire, onStartScenario, onStopScenario, onReset } = {}) {
  const [showHelp, setShowHelp] = useState(false)

  const closeHelp = useCallback(() => setShowHelp(false), [])

  useEffect(() => {
    if (!active) return

    const handler = (e) => {
      // Don't intercept when typing in inputs
      const tag = e.target?.tagName?.toUpperCase()
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
      if (e.metaKey || e.ctrlKey || e.altKey) return

      switch (e.key) {
        case 'd':
        case 'D':
          e.preventDefault()
          onFire?.()
          break
        case 's':
        case 'S':
          e.preventDefault()
          onStartScenario?.()
          break
        case 'x':
        case 'X':
          e.preventDefault()
          onStopScenario?.()
          break
        case 'r':
        case 'R':
          e.preventDefault()
          onReset?.()
          break
        case '?':
          e.preventDefault()
          setShowHelp(h => !h)
          break
        case 'Escape':
          setShowHelp(false)
          break
        default:
          break
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [active, onFire, onStartScenario, onStopScenario, onReset])

  return { showHelp, closeHelp }
}

// ── Shortcuts help modal ──────────────────────────────────────────────────────

const T = {
  bg:     '#0a0a0a',
  border: 'rgba(255,255,255,0.12)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

const SHORTCUTS = [
  { key: 'D', action: 'Fire random attack' },
  { key: 'S', action: 'Start scenario' },
  { key: 'X', action: 'Stop scenario' },
  { key: 'R', action: 'Open reset confirmation' },
  { key: '?', action: 'Show/hide this help' },
  { key: 'Esc', action: 'Close this help' },
]

export function ShortcutsHelp({ onClose }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 500,
        background: 'rgba(0,0,0,0.75)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: T.bg,
          border: `1px solid ${T.border}`,
          borderRadius: '14px',
          padding: '24px 28px',
          minWidth: '320px',
          boxShadow: '0 8px 40px rgba(0,0,0,0.9)',
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        <div style={{ fontSize: '13px', fontWeight: 700, color: T.text, marginBottom: '18px', letterSpacing: '-0.01em', fontFamily: "'Space Grotesk', sans-serif" }}>
          Demo Keyboard Shortcuts
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', fontSize: '9px', color: T.dim, fontWeight: 600, letterSpacing: '0.10em', textTransform: 'uppercase', paddingBottom: '8px', borderBottom: `1px solid ${T.border}` }}>Key</th>
              <th style={{ textAlign: 'left', fontSize: '9px', color: T.dim, fontWeight: 600, letterSpacing: '0.10em', textTransform: 'uppercase', paddingBottom: '8px', borderBottom: `1px solid ${T.border}` }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {SHORTCUTS.map(({ key, action }) => (
              <tr key={key}>
                <td style={{ padding: '7px 0', paddingRight: '24px', borderBottom: `1px solid rgba(255,255,255,0.05)` }}>
                  <span style={{
                    display: 'inline-block', minWidth: '28px', padding: '2px 7px',
                    background: 'rgba(255,255,255,0.08)', border: `1px solid ${T.border}`,
                    borderRadius: '5px', textAlign: 'center', fontSize: '11px',
                    fontWeight: 700, color: T.text, letterSpacing: '0.04em',
                  }}>{key}</span>
                </td>
                <td style={{ padding: '7px 0', fontSize: '11px', color: T.muted, borderBottom: `1px solid rgba(255,255,255,0.05)` }}>
                  {action}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <button
          onClick={onClose}
          style={{
            marginTop: '16px', width: '100%', padding: '7px',
            background: 'rgba(255,255,255,0.06)', border: `1px solid ${T.border}`,
            borderRadius: '7px', color: T.muted, fontFamily: "'IBM Plex Mono', monospace",
            fontSize: '10px', cursor: 'pointer', letterSpacing: '0.04em',
          }}
        >
          Close (Esc)
        </button>
      </div>
    </div>
  )
}
