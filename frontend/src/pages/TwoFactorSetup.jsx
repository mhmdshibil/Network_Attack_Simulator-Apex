/**
 * TwoFactorSetup — Phase 6B.
 * Accessible via Settings gear in sidebar or /settings/2fa route.
 * Shows 2FA status, QR setup flow, and disable flow.
 */
import React, { useState, useEffect, useCallback } from 'react'
import { Shield, ShieldOff, ShieldCheck } from 'lucide-react'
import './TwoFactorSetup.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('apex_token')
  return fetch(url, {
    ...opts,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  })
}

export default function TwoFactorSetup() {
  const [status,   setStatus]   = useState(null)
  const [setup,    setSetup]    = useState(null)   // {secret, qr_code_base64, backup_codes}
  const [code,     setCode]     = useState('')
  const [disCode,  setDisCode]  = useState('')
  const [phase,    setPhase]    = useState('idle') // idle | setting_up | disabling | done
  const [error,    setError]    = useState('')
  const [working,  setWorking]  = useState(false)

  const loadStatus = useCallback(async () => {
    try {
      const r = await authFetch(`${API_BASE}/api/auth/2fa/status`)
      if (r.ok) setStatus(await r.json())
    } catch (_) {}
  }, [])

  useEffect(() => { loadStatus() }, [loadStatus])

  async function startSetup() {
    setWorking(true); setError('')
    try {
      const r = await authFetch(`${API_BASE}/api/auth/2fa/setup`, { method: 'POST' })
      const j = await r.json()
      if (!r.ok) { setError(j.detail || 'Setup failed'); setWorking(false); return }
      setSetup(j)
      setPhase('setting_up')
    } catch (e) { setError(String(e)) }
    setWorking(false)
  }

  async function activate() {
    if (code.length < 6) { setError('Enter the 6-digit code from your app'); return }
    setWorking(true); setError('')
    try {
      const r = await authFetch(`${API_BASE}/api/auth/2fa/activate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      const j = await r.json()
      if (!r.ok) { setError(j.detail || 'Activation failed'); setWorking(false); return }
      setPhase('done'); setCode('')
      await loadStatus()
    } catch (e) { setError(String(e)) }
    setWorking(false)
  }

  async function disable() {
    if (!disCode.trim()) { setError('Enter your TOTP code to confirm'); return }
    setWorking(true); setError('')
    try {
      const r = await authFetch(`${API_BASE}/api/auth/2fa/disable`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: disCode }),
      })
      const j = await r.json()
      if (!r.ok) { setError(j.detail || 'Disable failed'); setWorking(false); return }
      setPhase('idle'); setDisCode('')
      await loadStatus()
    } catch (e) { setError(String(e)) }
    setWorking(false)
  }

  if (!status) return <div className="tfa-setup-loading">Loading…</div>

  return (
    <div className="tfa-setup-page">
      <div className="tfa-setup-eyebrow">Settings</div>
      <div className="tfa-setup-title">
        <Shield size={16} style={{ opacity: 0.6 }} /> Two-Factor Authentication
      </div>

      {/* Status banner */}
      <div className={`tfa-setup-banner ${status.enabled ? 'active' : 'inactive'}`}>
        {status.enabled
          ? <><ShieldCheck size={14} /><span>2FA is active on your account</span></>
          : <><ShieldOff  size={14} /><span>2FA is not enabled</span></>
        }
        {!status.totp_enabled_globally && (
          <span className="tfa-setup-note">
            (TOTP_ENABLED=false — 2FA is configured but not enforced at login)
          </span>
        )}
      </div>

      {/* ── Not enabled: setup flow ───────────────────────────────────────── */}
      {!status.enabled && phase === 'idle' && (
        <div className="tfa-setup-card">
          <p>Enable 2FA to protect your account with Google Authenticator or any TOTP app.</p>
          <button className="tfa-setup-btn primary" onClick={startSetup} disabled={working}>
            {working ? 'Generating…' : 'Enable 2FA'}
          </button>
          {error && <div className="tfa-setup-error">{error}</div>}
        </div>
      )}

      {phase === 'setting_up' && setup && (
        <div className="tfa-setup-card">
          <div className="tfa-setup-step">1. Scan this QR code with your authenticator app</div>
          <div className="tfa-qr-wrap">
            <img
              src={`data:image/png;base64,${setup.qr_code_base64}`}
              alt="QR Code"
              className="tfa-qr-img"
            />
          </div>
          <div className="tfa-setup-step">Or enter manually: <code className="tfa-secret">{setup.secret}</code></div>

          <div className="tfa-setup-step" style={{ marginTop: 20 }}>2. Save these backup codes (shown once)</div>
          <div className="tfa-backup-grid">
            {setup.backup_codes.map((c, i) => (
              <code key={i} className="tfa-backup-code">{c}</code>
            ))}
          </div>

          <div className="tfa-setup-step" style={{ marginTop: 20 }}>3. Enter the 6-digit code from your app to confirm</div>
          <input className="tfa-setup-code-input" type="text" inputMode="numeric"
            maxLength={6} value={code} placeholder="000000"
            onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />

          {error && <div className="tfa-setup-error">{error}</div>}

          <div className="tfa-setup-row">
            <button className="tfa-setup-btn secondary" onClick={() => { setPhase('idle'); setSetup(null); setError('') }}>
              Cancel
            </button>
            <button className="tfa-setup-btn primary" onClick={activate} disabled={working}>
              {working ? 'Activating…' : 'Activate 2FA'}
            </button>
          </div>
        </div>
      )}

      {phase === 'done' && (
        <div className="tfa-setup-card tfa-setup-success">
          <ShieldCheck size={28} />
          <div>2FA activated successfully!</div>
        </div>
      )}

      {/* ── Already enabled: disable flow ────────────────────────────────── */}
      {status.enabled && phase === 'idle' && (
        <div className="tfa-setup-card">
          <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: 13 }}>
            Enter your current TOTP code to disable 2FA.
          </p>
          <input className="tfa-setup-code-input" type="text" inputMode="numeric"
            maxLength={6} placeholder="000000" value={disCode}
            onChange={e => setDisCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
          {error && <div className="tfa-setup-error">{error}</div>}
          <button className="tfa-setup-btn danger" onClick={disable} disabled={working}>
            {working ? 'Disabling…' : 'Disable 2FA'}
          </button>
        </div>
      )}
    </div>
  )
}
