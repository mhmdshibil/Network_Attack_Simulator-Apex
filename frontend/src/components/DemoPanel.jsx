import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Zap, ChevronDown, Clock, Radio } from 'lucide-react'
import { enableDemo, disableDemo, triggerDemoAttack, fetchDemoStatus } from '../api/api'

const CLASSES = ['port_scan', 'ddos', 'bruteforce', 'sql_injection', 'malware']

const T = {
  bg:     '#0a0a0a',
  border: 'rgba(255,255,255,0.12)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
}

function fmtCountdown(s) {
  if (s == null) return null
  const m = Math.floor(s / 60), r = s % 60
  return m > 0 ? `${m}m ${String(r).padStart(2, '0')}s` : `${s}s`
}

// ── Monochrome pill toggle ────────────────────────────────────────────────────
function Toggle({ on, loading, onToggle }) {
  return (
    <button
      onClick={onToggle}
      disabled={loading}
      title={on ? 'Disable demo scheduler' : 'Enable demo scheduler'}
      style={{
        position: 'relative',
        width: '36px', height: '20px',
        background: on ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.12)',
        border: `1px solid ${on ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.20)'}`,
        borderRadius: '10px',
        cursor: loading ? 'not-allowed' : 'pointer',
        transition: 'background 0.18s, border-color 0.18s',
        boxShadow: on ? '0 0 8px rgba(255,255,255,0.20)' : 'none',
        flexShrink: 0,
        padding: 0,
      }}
    >
      <span style={{
        position: 'absolute',
        top: '3px',
        left: on ? '18px' : '3px',
        width: '12px', height: '12px',
        background: on ? '#000' : 'rgba(255,255,255,0.5)',
        borderRadius: '50%',
        transition: 'left 0.18s, background 0.18s',
      }} />
    </button>
  )
}

// ── Class picker dropdown ─────────────────────────────────────────────────────
function ClassPicker({ selected, onChange }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [open])

  const label = selected === 'random' ? 'Random' : selected.replace(/_/g, ' ')

  return (
    <div ref={ref} style={{ position: 'relative', flex: 1 }}>
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
          fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px',
          cursor: 'pointer', textAlign: 'left',
          transition: 'border-color 0.12s',
        }}
      >
        <span>{label}</span>
        <ChevronDown size={11} style={{ opacity: 0.5, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.12s', flexShrink: 0 }} />
      </button>

      {open && (
        <div style={{
          position: 'absolute', bottom: 'calc(100% + 6px)', left: 0, right: 0,
          background: '#111', border: `1px solid rgba(255,255,255,0.14)`,
          borderRadius: '8px', overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0,0,0,0.8)', zIndex: 10,
        }}>
          {['random', ...CLASSES].map(cls => (
            <button
              key={cls}
              onClick={() => { onChange(cls); setOpen(false) }}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '8px 12px', border: 'none',
                background: selected === cls ? 'rgba(255,255,255,0.08)' : 'transparent',
                color: selected === cls ? T.text : T.muted,
                fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px',
                fontWeight: selected === cls ? 600 : 400, cursor: 'pointer',
              }}
            >
              {cls === 'random' ? 'Random' : cls.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────
function DemoPanel() {
  const [selected, setSelected]   = useState('random')
  const [firing, setFiring]       = useState(false)
  const [toggling, setToggling]   = useState(false)
  const [last, setLast]           = useState(null)
  const [status, setStatus]       = useState(null)
  const [countdown, setCountdown] = useState(null)
  const [err, setErr]             = useState(null)

  // ── Status polling ──────────────────────────────────────────────────────────
  const refreshStatus = useCallback(async () => {
    try {
      const s = await fetchDemoStatus()
      setStatus(s)
      // Seed local countdown from server value
      setCountdown(s.next_fire_in_seconds ?? null)
    } catch {}
  }, [])

  useEffect(() => {
    refreshStatus()
    const iv = setInterval(refreshStatus, 5000)
    return () => clearInterval(iv)
  }, [refreshStatus])

  // Local 1-second ticker between polls
  useEffect(() => {
    if (!status?.enabled || countdown == null) return
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => Math.max(0, (c ?? 0) - 1)), 1000)
    return () => clearTimeout(t)
  }, [status?.enabled, countdown])

  // ── Toggle ──────────────────────────────────────────────────────────────────
  const handleToggle = useCallback(async () => {
    if (toggling) return
    setToggling(true)
    setErr(null)
    try {
      const s = status?.enabled ? await disableDemo() : await enableDemo()
      setStatus(s)
      setCountdown(s.next_fire_in_seconds ?? null)
    } catch (e) {
      setErr(e.message)
    } finally {
      setToggling(false)
    }
  }, [status?.enabled, toggling])

  // ── Manual trigger ──────────────────────────────────────────────────────────
  const handleFire = useCallback(async () => {
    if (firing) return
    setFiring(true)
    setErr(null)
    try {
      const cls = selected === 'random' ? null : selected
      const result = await triggerDemoAttack(cls)
      setLast(result)
      await refreshStatus()
    } catch (e) {
      setErr(e.message)
    } finally {
      setFiring(false)
    }
  }, [selected, firing, refreshStatus])

  const enabled    = status?.enabled ?? false
  const lastResult = last ?? status?.last_triggered

  return (
    <div style={{
      position: 'fixed', bottom: '20px', right: '24px', zIndex: 200,
      background: `linear-gradient(${T.bg}, ${T.bg}) padding-box,
                   linear-gradient(135deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.05) 100%) border-box`,
      border: '1px solid transparent',
      borderRadius: '14px',
      boxShadow: `0 0 0 1px rgba(255,255,255,0.06), 0 8px 32px rgba(0,0,0,0.85)${enabled ? ', 0 0 20px rgba(255,255,255,0.04)' : ''}`,
      padding: '14px 16px',
      minWidth: '270px', maxWidth: '300px',
      transition: 'box-shadow 0.3s',
    }}>
      {/* ── Header: label + toggle ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <Radio size={11} style={{ color: enabled ? 'rgba(255,255,255,0.9)' : T.muted, flexShrink: 0, transition: 'color 0.2s' }} />
        <span style={{
          fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px',
          fontWeight: enabled ? 700 : 600,
          color: enabled ? T.text : T.muted,
          letterSpacing: '0.10em', textTransform: 'uppercase',
          transition: 'color 0.2s, font-weight 0.2s',
        }}>
          Demo Mode
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Countdown badge — visible only when enabled */}
          {enabled && countdown != null && (
            <span style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px',
              color: T.muted, letterSpacing: '0.04em',
            }}>
              <Clock size={9} />
              {fmtCountdown(countdown)}
            </span>
          )}
          <Toggle on={enabled} loading={toggling} onToggle={handleToggle} />
        </div>
      </div>

      {/* ── State label ── */}
      <div style={{
        fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px',
        color: enabled ? 'rgba(255,255,255,0.45)' : T.dim,
        marginBottom: '10px', letterSpacing: '0.05em',
      }}>
        {toggling
          ? (enabled ? 'stopping…' : 'starting…')
          : enabled
            ? `auto-fires every ${status?.interval_seconds ?? 150}s`
            : 'scheduler off — manual trigger still works'}
      </div>

      {/* ── Class picker + Fire button ── */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <ClassPicker selected={selected} onChange={setSelected} />
        <button
          onClick={handleFire}
          disabled={firing}
          style={{
            display: 'flex', alignItems: 'center', gap: '5px',
            padding: '7px 12px',
            background: firing ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.12)',
            border: `1px solid ${firing ? T.border : 'rgba(255,255,255,0.28)'}`,
            borderRadius: '8px',
            color: firing ? T.muted : T.text,
            fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 600,
            cursor: firing ? 'not-allowed' : 'pointer',
            flexShrink: 0, transition: 'all 0.12s',
            boxShadow: firing ? 'none' : '0 0 8px rgba(255,255,255,0.06)',
          }}
        >
          <Zap size={11} style={{ animation: firing ? 'spin 0.6s linear infinite' : 'none' }} />
          {firing ? '…' : 'Fire'}
        </button>
      </div>

      {/* ── Last fired ── */}
      {lastResult && (
        <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: `1px solid ${T.border}` }}>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.dim, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
            Last fired
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '5px', height: '5px', background: 'rgba(255,255,255,0.7)', borderRadius: '50%', boxShadow: '0 0 4px rgba(255,255,255,0.4)', flexShrink: 0 }} />
            <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', color: T.text, fontWeight: 600 }}>
              {lastResult.class?.replace(/_/g, ' ')}
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, marginLeft: 'auto' }}>
              {new Date(lastResult.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.dim, marginTop: '2px', paddingLeft: '11px' }}>
            {lastResult.detections} detection{lastResult.detections !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {err && (
        <div style={{ marginTop: '8px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: 'rgba(255,255,255,0.45)', borderTop: `1px solid ${T.border}`, paddingTop: '8px' }}>
          {err}
        </div>
      )}
    </div>
  )
}

export default DemoPanel
