import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('apex_token'))
  const [role, setRole] = useState(() => localStorage.getItem('apex_role') || null)
  const [authRequired, setAuthRequired] = useState(false)
  const [llmConfigured, setLlmConfigured] = useState(false)
  const [demoMode, setDemoMode] = useState(false)
  const [loginError, setLoginError] = useState(null)
  const [showLogin, setShowLogin] = useState(false)

  // Check server-side feature flags on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/auth/status`)
      .then(r => r.json())
      .then(d => {
        setAuthRequired(d.auth_enabled === true)
        setLlmConfigured(d.llm_configured === true)
        setDemoMode(d.demo_mode === true)
        if (d.auth_enabled && !token) setShowLogin(true)
      })
      .catch(() => {})
  }, [])

  const login = useCallback(async (username, password) => {
    setLoginError(null)
    const form = new URLSearchParams({ username, password, grant_type: 'password' })
    try {
      const res = await fetch(`${API_BASE}/api/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      })
      if (!res.ok) {
        const err = await res.json()
        setLoginError(err.detail || 'Login failed')
        return false
      }
      const data = await res.json()
      localStorage.setItem('apex_token', data.access_token)
      localStorage.setItem('apex_role', data.role)
      setToken(data.access_token)
      setRole(data.role)
      setShowLogin(false)
      return true
    } catch (e) {
      setLoginError('Network error')
      return false
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('apex_token')
    localStorage.removeItem('apex_role')
    setToken(null)
    setRole(null)
    if (authRequired) setShowLogin(true)
  }, [authRequired])

  // Called by api.js when a 401 is received
  const onUnauthorized = useCallback(() => {
    if (authRequired) setShowLogin(true)
  }, [authRequired])

  return (
    <AuthContext.Provider value={{ token, role, authRequired, llmConfigured, demoMode, login, logout, loginError, showLogin, setShowLogin, onUnauthorized }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
