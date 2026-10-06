/**
 * NLQBar — Phase 6D: Natural Language Query bar.
 * Floats below page title on Detected Attacks page.
 * Press / to focus. Enter to query. × to clear.
 */
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Search, X, Loader } from 'lucide-react'
import { useToast } from '../context/ToastContext'
import './NLQBar.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('apex_token')
  return fetch(url, {
    ...opts,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  })
}

export default function NLQBar({ onResults, onClear }) {
  const { showToast } = useToast()
  const [value,   setValue]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [filters, setFilters] = useState(null)  // parsed filter badges
  const [active,  setActive]  = useState(false) // showing NLQ results
  const inputRef = useRef(null)

  // Press / to focus the bar (when not already in an input)
  useEffect(() => {
    function onKey(e) {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' &&
          document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const handleSubmit = useCallback(async () => {
    const q = value.trim()
    if (!q) return
    setLoading(true); setError(''); setFilters(null)
    try {
      const r = await authFetch(`${API_BASE}/api/nlq`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      })
      const j = await r.json()
      if (j.error) {
        setError(j.error)
        showToast(j.error, 'error')
        setLoading(false)
        return
      }
      setFilters(j.parsed_filters || {})
      setActive(true)
      onResults({ results: j.results, count: j.result_count, query: q, queryMs: j.query_time_ms })
      if (j.result_count === 0) showToast('No results for that query', 'info')
    } catch (e) {
      setError('Network error')
      showToast('Query failed — network error', 'error')
    }
    setLoading(false)
  }, [value, onResults, showToast])

  function handleClear() {
    setValue(''); setError(''); setFilters(null); setActive(false)
    onClear()
  }

  function handleKey(e) {
    if (e.key === 'Enter') handleSubmit()
    if (e.key === 'Escape') { inputRef.current?.blur(); if (!value) handleClear() }
  }

  const filterBadges = filters
    ? Object.entries(filters).filter(([k]) => !k.startsWith('_'))
    : []

  return (
    <div className="nlq-wrap">
      <div className={`nlq-bar ${error ? 'nlq-bar-error' : ''} ${active ? 'nlq-bar-active' : ''}`}>
        <Search size={14} className="nlq-icon" />
        <input
          ref={inputRef}
          className="nlq-input"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder='Ask anything… e.g. "show bruteforce attacks from Russia this week"'
          disabled={loading}
        />
        {loading && <Loader size={14} className="nlq-spinner" />}
        {(value || active) && !loading && (
          <button className="nlq-clear" onClick={handleClear}><X size={13} /></button>
        )}
      </div>

      {error && <div className="nlq-error">{error}</div>}

      {filterBadges.length > 0 && (
        <div className="nlq-badges">
          {filterBadges.map(([k, v]) => (
            <span key={k} className="nlq-badge">
              {k.replace(/_/g, ' ')}: {Array.isArray(v) ? v.join(', ') : String(v)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
