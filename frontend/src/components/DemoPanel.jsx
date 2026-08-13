import React, { useState, useEffect, useCallback } from 'react'
import { Zap, ChevronDown, Clock, Radio } from 'lucide-react'
import { triggerDemoAttack, fetchDemoStatus } from '../api/api'

const CLASSES = ['port_scan', 'ddos', 'bruteforce', 'sql_injection', 'malware']

const T = {
  bg:     '#0a0a0a',
  border: 'rgba(255,255,255,0.12)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

function fmtCountdown(seconds) {
  if (seconds == null) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

function DemoPanel() {
  const [selected, setSelected] = useState('random')
  const [open, setOpen] = useState(false)
  const [firing, setFiring] = useState(false)
  const [last, setLast] = useState(null)      // { class, ip, at, detections }
  const [status, setStatus] = useState(null)  // from /api/demo/status
  const [error, setError] = useState(null)

  // Poll status every 5 s for countdown + last_triggered
  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const s = await fetchDemoStatus()
        if (!cancelled) setStatus(s)
      } catch {}
    }
    poll()
    const iv = setInterval(poll, 5000)
    return () => { cancelled = true; clearInterval(iv) }
  }, [])

  // Tick countdown locally between polls
  const [localCountdown, setLocalCountdown] = useState(null)
  useEffect(() => {
    if (status?.next_fire_in_seconds == null) return
    setLocalCountdown(status.next_fire_in_seconds)
  }, [status?.next_fire_in_seconds])

  useEffect(() => {
    if (localCountdown == null || localCountdown <= 0) return
    const t = setTimeout(() => setLocalCountdown(c => Math.max(0, c - 1)), 1000)
    return () => clearTimeout(t)
  }, [localCountdown])

  const trigger = useCallback(async () => {
    setFiring(true)
    setError(null)
    try {
      const cls = selected === 'random' ? null : selected
      const result = await triggerDemoAttack(cls)
      setLast(result)
      // Refresh status after trigger
      const s = await fetchDemoStatus()
      setStatus(s)
    } catch (e) {
      setError(e.message)
    } finally {
      setFiring(false)
    }
  }, [selected])

  const displayLabel = selected === 'random' ? 'Random' : selected.replace('_', ' ')

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '24px',
      zIndex: 200,
      background: `linear-gradient(${T.bg}, ${T.bg}) padding-box,
                   linear-gradient(135deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.05) 100%) border-box`,
      border: '1px solid transparent',
      borderRadius: '14px',
      boxShadow: '0 0 0 1px rgba(255,255,255,0.06), 0 8px 32px rgba(0,0,0,0.85)',
      padding: '14px 16px',
      minWidth: '260px',
      maxWidth: '300px',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '12px' }}>
        <Radio size={11} style={{ color: 'rgba(255,255,255,0.8)', flexShrink: 0 }} />
        <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 700, color: T.text, letterSpacing: '0.10em', textTransform: 'uppercase' }}>
          Demo Mode
        </span>
        {status?.next_fire_in_seconds != null && (
          <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '4px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.muted }}>
            <Clock size={9} />
            {fmtCountdown(localCountdown)}
          </span>
        )}
      </div>

      {/* Class picker + trigger row */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        {/* Custom dropdown */}
        <div style={{ position: 'relative', flex: 1 }}>
          <button
            onClick={() => setOpen(o => !o)}
            style={{
              width: '100%',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px',
              padding: '7px 10px',
              background: 'rgba(255,255,255,0.06)',
              border: `1px solid ${open ? 'rgba(255,255,255,0.22)' : T.border}`,
              borderRadius: '8px',
              color: T.text,
              fontFamily: "'IBM Plex Mono',monospace",
              fontSize: '11px',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'border-color 0.12s',
            }}
          >
            <span>{displayLabel}</span>
            <ChevronDown size={11} style={{ opacity: 0.5, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.12s', flexShrink: 0 }} />
          </button>

          {open && (
            <div style={{
              position: 'absolute',
              bottom: 'calc(100% + 6px)',
              left: 0, right: 0,
              background: '#111',
              border: `1px solid rgba(255,255,255,0.14)`,
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 4px 20px rgba(0,0,0,0.8)',
              zIndex: 10,
            }}>
              {['random', ...CLASSES].map(cls => (
                <button
                  key={cls}
                  onClick={() => { setSelected(cls); setOpen(false) }}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '8px 12px',
                    background: selected === cls ? 'rgba(255,255,255,0.08)' : 'transparent',
                    border: 'none',
                    color: selected === cls ? T.text : T.muted,
                    fontFamily: "'IBM Plex Mono',monospace",
                    fontSize: '11px',
                    fontWeight: selected === cls ? 600 : 400,
                    cursor: 'pointer',
                    transition: 'background 0.1s, color 0.1s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.06)'}
                  onMouseLeave={e => e.currentTarget.style.background = selected === cls ? 'rgba(255,255,255,0.08)' : 'transparent'}
                >
                  {cls === 'random' ? 'Random' : cls.replace('_', ' ')}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Trigger button */}
        <button
          onClick={trigger}
          disabled={firing}
          style={{
            display: 'flex', alignItems: 'center', gap: '5px',
            padding: '7px 12px',
            background: firing ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.12)',
            border: `1px solid ${firing ? T.border : 'rgba(255,255,255,0.28)'}`,
            borderRadius: '8px',
            color: firing ? T.muted : T.text,
            fontFamily: "'IBM Plex Mono',monospace",
            fontSize: '11px',
            fontWeight: 600,
            cursor: firing ? 'not-allowed' : 'pointer',
            flexShrink: 0,
            transition: 'background 0.12s, border-color 0.12s, color 0.12s',
            boxShadow: firing ? 'none' : '0 0 8px rgba(255,255,255,0.06)',
          }}
        >
          <Zap size={11} style={{ animation: firing ? 'spin 0.6s linear infinite' : 'none' }} />
          {firing ? '…' : 'Fire'}
        </button>
      </div>

      {/* Last result */}
      {(last || status?.last_triggered) && (() => {
        const r = last || status.last_triggered
        const time = new Date(r.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        return (
          <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: `1px solid ${T.border}` }}>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
              Last fired
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '5px', height: '5px', background: 'rgba(255,255,255,0.7)', borderRadius: '50%', boxShadow: '0 0 4px rgba(255,255,255,0.4)', flexShrink: 0 }} />
              <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, fontWeight: 600 }}>
                {r.class?.replace('_', ' ')}
              </span>
              <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, marginLeft: 'auto' }}>
                {time}
              </span>
            </div>
            <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, marginTop: '2px', paddingLeft: '11px' }}>
              {r.detections} detection{r.detections !== 1 ? 's' : ''}
            </div>
          </div>
        )
      })()}

      {/* Error */}
      {error && (
        <div style={{ marginTop: '8px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: 'rgba(255,255,255,0.5)', borderTop: `1px solid ${T.border}`, paddingTop: '8px' }}>
          {error}
        </div>
      )}
    </div>
  )
}

export default DemoPanel
