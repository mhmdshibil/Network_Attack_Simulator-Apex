import React, { useState } from 'react'
import { useAuth } from '../context/AuthContext'

export default function LoginModal() {
  const { login, loginError, showLogin, setShowLogin, authRequired } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  if (!showLogin) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    await login(username, password)
    setLoading(false)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
    }}>
      <div style={{
        background: '#0d1117', border: '1px solid #30363d', borderRadius: 12,
        padding: '2rem', width: 360, boxShadow: '0 0 40px rgba(0,180,255,0.15)',
      }}>
        <h2 style={{ color: '#58a6ff', marginBottom: '0.25rem', fontSize: '1.25rem' }}>APEX SOC</h2>
        <p style={{ color: '#8b949e', fontSize: '0.8rem', marginBottom: '1.5rem' }}>Authentication required</p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.8rem', marginBottom: 4 }}>Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              autoFocus
              style={{
                width: '100%', boxSizing: 'border-box',
                background: '#161b22', border: '1px solid #30363d', borderRadius: 6,
                color: '#c9d1d9', padding: '0.5rem 0.75rem', fontSize: '0.9rem',
              }}
            />
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', color: '#c9d1d9', fontSize: '0.8rem', marginBottom: 4 }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              style={{
                width: '100%', boxSizing: 'border-box',
                background: '#161b22', border: '1px solid #30363d', borderRadius: 6,
                color: '#c9d1d9', padding: '0.5rem 0.75rem', fontSize: '0.9rem',
              }}
            />
          </div>

          {loginError && (
            <p style={{ color: '#f85149', fontSize: '0.8rem', marginBottom: '0.75rem' }}>{loginError}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%', padding: '0.6rem', borderRadius: 6, border: 'none',
              background: loading ? '#1f6feb88' : '#1f6feb',
              color: '#fff', fontSize: '0.9rem', cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p style={{ color: '#8b949e', fontSize: '0.7rem', marginTop: '1rem', textAlign: 'center' }}>
          Default: admin / adminpass &nbsp;·&nbsp; analyst / analystpass
        </p>
      </div>
    </div>
  )
}
