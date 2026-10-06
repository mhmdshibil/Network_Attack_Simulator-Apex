/**
 * TwoFactorModal — shown after login when the server returns requires_2fa=true.
 * 6 individual digit inputs with auto-advance + paste support.
 */
import React, { useState, useRef, useCallback } from 'react'
import './TwoFactorModal.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export default function TwoFactorModal({ tempToken, onSuccess, onCancel }) {
  const [digits,   setDigits]   = useState(Array(6).fill(''))
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [backup,   setBackup]   = useState(false)
  const [backupCode, setBackupCode] = useState('')
  const inputsRef = useRef([])

  const handleDigit = useCallback((i, val) => {
    // Allow pasting full code into first box
    if (val.length > 1) {
      const clean = val.replace(/\D/g, '').slice(0, 6)
      const next  = Array(6).fill('')
      clean.split('').forEach((d, idx) => { next[idx] = d })
      setDigits(next)
      inputsRef.current[Math.min(clean.length, 5)]?.focus()
      return
    }
    if (!/^\d?$/.test(val)) return
    const next = [...digits]
    next[i] = val
    setDigits(next)
    if (val && i < 5) inputsRef.current[i + 1]?.focus()
  }, [digits])

  const handleKey = useCallback((i, e) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) {
      inputsRef.current[i - 1]?.focus()
    }
  }, [digits])

  const handleSubmit = useCallback(async () => {
    const code = backup ? backupCode : digits.join('')
    if (!backup && code.length < 6) { setError('Enter all 6 digits'); return }
    if (backup && !code.trim())     { setError('Enter backup code');   return }
    setLoading(true); setError('')
    try {
      const r = await fetch(`${API_BASE}/api/auth/2fa/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_token: tempToken, code }),
      })
      const j = await r.json()
      if (!r.ok) { setError(j.detail || 'Invalid code'); setLoading(false); return }
      onSuccess(j.access_token, j.role || 'analyst')
    } catch (e) {
      setError('Network error')
    }
    setLoading(false)
  }, [digits, backup, backupCode, tempToken, onSuccess])

  return (
    <div className="tfa-overlay">
      <div className="tfa-modal">
        <div className="tfa-title">Two-Factor Authentication</div>
        <div className="tfa-sub">
          {backup ? 'Enter a backup code' : 'Enter the 6-digit code from your authenticator app'}
        </div>

        {!backup ? (
          <div className="tfa-digits">
            {digits.map((d, i) => (
              <input
                key={i}
                ref={el => { inputsRef.current[i] = el }}
                className="tfa-digit"
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={d}
                onChange={e => handleDigit(i, e.target.value)}
                onKeyDown={e => handleKey(i, e)}
                autoFocus={i === 0}
              />
            ))}
          </div>
        ) : (
          <input
            className="tfa-backup-input"
            type="text"
            placeholder="xxxx-xxxx"
            value={backupCode}
            onChange={e => setBackupCode(e.target.value)}
            autoFocus
          />
        )}

        {error && <div className="tfa-error">{error}</div>}

        <button className="tfa-submit" onClick={handleSubmit} disabled={loading}>
          {loading ? 'Verifying…' : 'Verify'}
        </button>

        <div className="tfa-links">
          <button className="tfa-link" onClick={() => { setBackup(b => !b); setError('') }}>
            {backup ? '← Use authenticator code' : 'Use a backup code'}
          </button>
          {onCancel && (
            <button className="tfa-link tfa-cancel" onClick={onCancel}>Cancel</button>
          )}
        </div>
      </div>
    </div>
  )
}
