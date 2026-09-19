import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Zap, ChevronDown, Clock, Radio, Play, Square, RotateCcw, AlertTriangle } from 'lucide-react'
import {
  enableDemo, disableDemo, triggerDemoAttack, fetchDemoStatus,
  startScenario, stopScenario, fetchScenarioStatus,
  fetchMetrics, fetchSystemOverview, fetchTriageStats,
  resetDemo,
} from '../api/api'
import { useAuth } from '../context/AuthContext'

const CLASSES = ['port_scan', 'ddos', 'bruteforce', 'sql_injection', 'malware']

const T = {
  bg:     '#0a0a0a',
  border: 'rgba(255,255,255,0.12)',
  text:   '#ffffff',
  muted:  'rgba(255,255,255,0.55)',
  dim:    'rgba(255,255,255,0.28)',
  red:    'rgba(220,50,50,0.85)',
  redBg:  'rgba(200,40,40,0.10)',
  redBorder: 'rgba(200,40,40,0.28)',
}

const sectionHead = {
  fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px',
  fontWeight: 700, color: T.dim, letterSpacing: '0.12em',
  textTransform: 'uppercase', marginBottom: '8px', marginTop: '0',
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
        flexShrink: 0, padding: 0,
      }}
    >
      <span style={{
        position: 'absolute', top: '3px',
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
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '6px',
          padding: '7px 10px', background: 'rgba(255,255,255,0.06)',
          border: `1px solid ${open ? 'rgba(255,255,255,0.22)' : T.border}`,
          borderRadius: '8px', color: T.text,
          fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px',
          cursor: 'pointer', textAlign: 'left', transition: 'border-color 0.12s',
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
            <button key={cls} onClick={() => { onChange(cls); setOpen(false) }}
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

// ── Confirm Reset Modal ────────────────────────────────────────────────────────
function ResetModal({ onClose, onConfirm, resetting }) {
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
          background: T.bg, border: `1px solid ${T.border}`,
          borderRadius: '14px', padding: '24px 28px', maxWidth: '340px',
          boxShadow: '0 8px 40px rgba(0,0,0,0.9)',
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <AlertTriangle size={14} style={{ color: T.red }} />
          <span style={{ fontSize: '12px', fontWeight: 700, color: T.text, letterSpacing: '-0.01em', fontFamily: "'Space Grotesk',sans-serif" }}>
            Reset Demo Data
          </span>
        </div>
        <p style={{ fontSize: '11px', color: T.muted, lineHeight: '1.6', margin: '0 0 20px' }}>
          This will clear all detections, blocked IPs, and triage cases. Are you sure?
        </p>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: '8px', background: 'rgba(255,255,255,0.06)',
              border: `1px solid ${T.border}`, borderRadius: '8px', color: T.muted,
              fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={resetting}
            style={{
              flex: 1, padding: '8px', background: T.redBg,
              border: `1px solid ${T.redBorder}`, borderRadius: '8px', color: T.red,
              fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 700,
              cursor: resetting ? 'not-allowed' : 'pointer', opacity: resetting ? 0.6 : 1,
            }}
          >
            {resetting ? 'Resetting…' : 'Reset'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main panel ────────────────────────────────────────────────────────────────
function DemoPanel({ onResetRequest }) {
  const { role, authRequired } = useAuth()
  const isAdmin = !authRequired || role === 'admin'

  const [selected, setSelected]   = useState('random')
  const [firing, setFiring]       = useState(false)
  const [toggling, setToggling]   = useState(false)
  const [last, setLast]           = useState(null)
  const [status, setStatus]       = useState(null)
  const [countdown, setCountdown] = useState(null)
  const [err, setErr]             = useState(null)

  // Scenario state
  const [scenarioStatus, setScenarioStatus] = useState({ is_running: false, progress: 0, current_act: 0, act_name: '' })
  const [scenarioLoading, setScenarioLoading] = useState(false)

  // Quick stats
  const [stats, setStats] = useState({ detections: '—', blocked: '—', triageOpen: '—' })

  // Reset modal (if not delegated)
  const [showReset, setShowReset] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [resetMsg, setResetMsg]   = useState(null)

  // ── Status polling ──────────────────────────────────────────────────────────
  const refreshStatus = useCallback(async () => {
    try {
      const s = await fetchDemoStatus()
      setStatus(s)
      setCountdown(s.next_fire_in_seconds ?? null)
    } catch {}
  }, [])

  useEffect(() => {
    refreshStatus()
    const iv = setInterval(refreshStatus, 5000)
    return () => clearInterval(iv)
  }, [refreshStatus])

  // Local 1-second ticker
  useEffect(() => {
    if (!status?.enabled || countdown == null) return
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => Math.max(0, (c ?? 0) - 1)), 1000)
    return () => clearTimeout(t)
  }, [status?.enabled, countdown])

  // ── Scenario status polling ─────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const s = await fetchScenarioStatus()
        setScenarioStatus(s)
      } catch {}
    }
    poll()
    const iv = setInterval(poll, 2000)
    return () => clearInterval(iv)
  }, [])

  // ── Quick stats polling ─────────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const [m, o, t] = await Promise.allSettled([
          fetchMetrics(), fetchSystemOverview(), fetchTriageStats(),
        ])
        setStats({
          detections: m.status === 'fulfilled' ? (m.value?.total_detections ?? '—') : '—',
          blocked:    o.status === 'fulfilled' ? (o.value?.blocked_ips ?? '—') : '—',
          triageOpen: t.status === 'fulfilled' ? (t.value?.open_count ?? '—') : '—',
        })
      } catch {}
    }
    poll()
    const iv = setInterval(poll, 5000)
    return () => clearInterval(iv)
  }, [])

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

  // ── Scenario controls ───────────────────────────────────────────────────────
  const handleScenarioToggle = useCallback(async () => {
    if (scenarioLoading) return
    setScenarioLoading(true)
    setErr(null)
    try {
      if (scenarioStatus.is_running) {
        await stopScenario()
      } else {
        await startScenario('corporate_breach')
      }
      const s = await fetchScenarioStatus()
      setScenarioStatus(s)
    } catch (e) {
      setErr(e.message)
    } finally {
      setScenarioLoading(false)
    }
  }, [scenarioStatus.is_running, scenarioLoading])

  // ── Reset ───────────────────────────────────────────────────────────────────
  const openReset = useCallback(() => {
    if (onResetRequest) { onResetRequest(); return }
    setShowReset(true)
  }, [onResetRequest])

  const handleReset = useCallback(async () => {
    setResetting(true)
    setResetMsg(null)
    try {
      await resetDemo()
      setResetMsg('System reset — ready for demo')
      setShowReset(false)
      setTimeout(() => { window.location.reload() }, 2000)
    } catch (e) {
      setResetMsg(e.message)
    } finally {
      setResetting(false)
    }
  }, [])

  const enabled    = status?.enabled ?? false
  const lastResult = last ?? status?.last_triggered
  const scenarioRunning = scenarioStatus?.is_running

  const divider = { borderTop: `1px solid ${T.border}`, margin: '12px 0' }
  const smallBtn = (extra = {}) => ({
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
    width: '100%', padding: '7px 12px',
    background: 'rgba(255,255,255,0.06)',
    border: `1px solid ${T.border}`,
    borderRadius: '8px', color: T.muted,
    fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 600,
    cursor: 'pointer', transition: 'all 0.12s', letterSpacing: '0.04em',
    ...extra,
  })

  return (
    <>
      {showReset && (
        <ResetModal
          onClose={() => setShowReset(false)}
          onConfirm={handleReset}
          resetting={resetting}
        />
      )}

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
        maxHeight: '90vh', overflowY: 'auto',
      }}>

        {/* ── Header: label + toggle ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Radio size={11} style={{ color: enabled ? 'rgba(255,255,255,0.9)' : T.muted, flexShrink: 0, transition: 'color 0.2s' }} />
          <span style={{
            fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px',
            fontWeight: enabled ? 700 : 600, color: enabled ? T.text : T.muted,
            letterSpacing: '0.10em', textTransform: 'uppercase', transition: 'color 0.2s, font-weight 0.2s',
          }}>
            Demo Mode
          </span>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {enabled && countdown != null && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.muted, letterSpacing: '0.04em' }}>
                <Clock size={9} />
                {fmtCountdown(countdown)}
              </span>
            )}
            <Toggle on={enabled} loading={toggling} onToggle={handleToggle} />
          </div>
        </div>

        {/* ── State label ── */}
        <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: enabled ? 'rgba(255,255,255,0.45)' : T.dim, marginBottom: '10px', letterSpacing: '0.05em' }}>
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
              display: 'flex', alignItems: 'center', gap: '5px', padding: '7px 12px',
              background: firing ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.12)',
              border: `1px solid ${firing ? T.border : 'rgba(255,255,255,0.28)'}`,
              borderRadius: '8px', color: firing ? T.muted : T.text,
              fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 600,
              cursor: firing ? 'not-allowed' : 'pointer', flexShrink: 0, transition: 'all 0.12s',
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

        {/* ══════════════════════════════════════════════════════ */}
        {/* SCENARIO PLAYER */}
        <div style={divider} />
        <div style={sectionHead}>Scenario Player</div>

        {/* Scenario card */}
        <div style={{
          background: 'rgba(255,255,255,0.03)', border: `1px solid ${T.border}`,
          borderRadius: '8px', padding: '10px 12px', marginBottom: '8px',
        }}>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 700, color: T.text, marginBottom: '3px' }}>
            Corporate Breach Attempt
          </div>
          <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.muted, marginBottom: '6px', letterSpacing: '0.03em' }}>
            3 min · 5 acts · recon → SQLi → malware → DDoS
          </div>

          {scenarioRunning && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.muted }}>
                  Act {scenarioStatus.current_act}/5 — {scenarioStatus.act_name}
                </span>
                <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '9px', color: T.dim }}>
                  {scenarioStatus.progress}%
                </span>
              </div>
              <div style={{ height: '3px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${scenarioStatus.progress}%`, height: '100%', background: 'rgba(200,40,40,0.7)', transition: 'width 0.6s ease' }} />
              </div>
            </div>
          )}

          <button
            onClick={handleScenarioToggle}
            disabled={scenarioLoading}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px',
              width: '100%', padding: '7px',
              background: scenarioRunning ? T.redBg : 'rgba(255,255,255,0.06)',
              border: `1px solid ${scenarioRunning ? T.redBorder : T.border}`,
              borderRadius: '7px',
              color: scenarioRunning ? T.red : T.muted,
              fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', fontWeight: 700,
              cursor: scenarioLoading ? 'not-allowed' : 'pointer', transition: 'all 0.12s',
              letterSpacing: '0.04em',
            }}
          >
            {scenarioRunning ? <Square size={9} /> : <Play size={9} />}
            {scenarioLoading ? '…' : scenarioRunning ? 'Stop Scenario' : 'Launch Scenario'}
          </button>
        </div>

        {/* ══════════════════════════════════════════════════════ */}
        {/* QUICK STATS */}
        <div style={divider} />
        <div style={sectionHead}>Quick Stats</div>

        {[
          { label: 'Detections', value: stats.detections },
          { label: 'IPs Blocked', value: stats.blocked },
          { label: 'Triage Open', value: stats.triageOpen },
        ].map(({ label, value }) => (
          <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
            <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted }}>{label}</span>
            <span style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '11px', fontWeight: 700, color: T.text }}>{value}</span>
          </div>
        ))}

        {/* ══════════════════════════════════════════════════════ */}
        {/* SYSTEM RESET (admin only) */}
        {isAdmin && (
          <>
            <div style={divider} />
            <div style={sectionHead}>System Reset</div>

            {resetMsg && (
              <div style={{ fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: T.muted, marginBottom: '6px', letterSpacing: '0.02em' }}>
                {resetMsg}
              </div>
            )}

            <button
              onClick={openReset}
              style={smallBtn({
                color: T.red, background: T.redBg,
                border: `1px solid ${T.redBorder}`,
              })}
            >
              <RotateCcw size={10} />
              Reset to Clean State
            </button>
          </>
        )}

        {/* ── Error ── */}
        {err && (
          <div style={{ marginTop: '8px', fontFamily: "'IBM Plex Mono',monospace", fontSize: '10px', color: 'rgba(255,255,255,0.45)', borderTop: `1px solid ${T.border}`, paddingTop: '8px' }}>
            {err}
          </div>
        )}

      </div>
    </>
  )
}

export default DemoPanel
