import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'

const S = {
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.85)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 9999,
    backdropFilter: 'blur(4px)',
  },
  panel: {
    background: 'linear-gradient(#0a0a0a, #0a0a0a) padding-box, linear-gradient(135deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.06) 100%) border-box',
    border: '1px solid transparent',
    borderRadius: '20px',
    padding: '36px 32px',
    width: 360,
    boxShadow: '0 0 0 1px rgba(255,255,255,0.06), 0 32px 64px rgba(0,0,0,0.9)',
  },
  eyebrow: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '10px',
    fontWeight: 600,
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    color: 'rgba(255,255,255,0.40)',
    marginBottom: '10px',
  },
  title: {
    fontFamily: "'Space Grotesk', sans-serif",
    fontSize: '24px',
    fontWeight: 700,
    color: '#fff',
    letterSpacing: '-0.02em',
    marginBottom: '6px',
  },
  subtitle: {
    fontFamily: "'Inter', sans-serif",
    fontSize: '13px',
    color: 'rgba(255,255,255,0.45)',
    marginBottom: '28px',
    lineHeight: '1.5',
  },
  label: {
    display: 'block',
    fontFamily: "'Inter', sans-serif",
    fontSize: '11px',
    fontWeight: 600,
    color: 'rgba(255,255,255,0.55)',
    marginBottom: '6px',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.14)',
    borderRadius: '10px',
    color: '#fff',
    padding: '10px 14px',
    fontSize: '14px',
    fontFamily: "'IBM Plex Mono', monospace",
    outline: 'none',
    transition: 'border-color 0.15s, box-shadow 0.15s',
  },
  inputFocusStyle: '0 0 0 2px rgba(255,255,255,0.20)',
  btnPrimary: {
    width: '100%',
    padding: '11px',
    borderRadius: '10px',
    border: '1px solid rgba(255,255,255,0.30)',
    background: 'rgba(255,255,255,0.10)',
    color: '#fff',
    fontSize: '14px',
    fontFamily: "'Space Grotesk', sans-serif",
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '-0.01em',
    transition: 'background 0.15s, box-shadow 0.15s',
  },
  btnDisabled: {
    opacity: 0.45,
    cursor: 'not-allowed',
  },
  error: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '11px',
    color: 'rgba(255,255,255,0.75)',
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.18)',
    borderRadius: '8px',
    padding: '8px 12px',
    marginBottom: '14px',
  },
  hint: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '10px',
    color: 'rgba(255,255,255,0.25)',
    marginTop: '16px',
    textAlign: 'center',
    letterSpacing: '0.02em',
  },
}

export default function LoginModal() {
  const { login, loginError, showLogin, authRequired } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [focused, setFocused]   = useState(null)

  if (!showLogin) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    await login(username, password)
    setLoading(false)
  }

  const inputStyle = (field) => ({
    ...S.input,
    borderColor: focused === field ? 'rgba(255,255,255,0.32)' : 'rgba(255,255,255,0.14)',
    boxShadow: focused === field ? S.inputFocusStyle : 'none',
  })

  return (
    <div style={S.overlay}>
      <div style={S.panel}>
        <div style={S.eyebrow}>Security Operations</div>
        <div style={S.title}>Apex-Kinetics</div>
        <div style={S.subtitle}>Sign in to access the SOC dashboard</div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={S.label}>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              onFocus={() => setFocused('user')}
              onBlur={() => setFocused(null)}
              required
              autoFocus
              style={inputStyle('user')}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={S.label}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onFocus={() => setFocused('pass')}
              onBlur={() => setFocused(null)}
              required
              style={inputStyle('pass')}
            />
          </div>

          {loginError && <div style={S.error}>{loginError}</div>}

          <button
            type="submit"
            disabled={loading}
            style={{ ...S.btnPrimary, ...(loading ? S.btnDisabled : {}) }}
          >
            {loading ? 'Authenticating…' : 'Sign in'}
          </button>
        </form>

        <div style={S.hint}>
          admin / adminpass · analyst / analystpass
        </div>
      </div>
    </div>
  )
}
