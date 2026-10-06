import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'

const WS_BASE  = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/^http/, 'ws')
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const BUFFER_SIZE = 100
const MAX_BACKOFF = 30000

export const DetectionStreamContext = createContext(null)

export function useDetectionStreamContext() {
  return useContext(DetectionStreamContext)
}

export function DetectionStreamProvider({ children }) {
  const subscribersRef = useRef(new Set())
  const wsRef          = useRef(null)
  const pollRef        = useRef(null)
  const retryTimerRef  = useRef(null)
  const [lastDetections, setLastDetections] = useState([])

  // broadcast is called for EVERY WS message type so subscribers can filter themselves
  const broadcast = useCallback((msg) => {
    if (msg.type === 'detection') {
      setLastDetections(prev => [msg, ...prev].slice(0, BUFFER_SIZE))
    }
    subscribersRef.current.forEach(cb => { try { cb(msg) } catch (_) {} })
  }, [])

  useEffect(() => {
    let dead    = false
    let backoff = 1000

    function stopPolling() {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }

    function startPolling() {
      if (pollRef.current) return
      const poll = async () => {
        try {
          const token   = localStorage.getItem('apex_token')
          const headers = token ? { Authorization: `Bearer ${token}` } : {}
          const res     = await fetch(`${API_BASE}/api/detections?limit=20`, { headers })
          if (res.status === 401) return
          const data = await res.json()
          const list = Array.isArray(data) ? data : []
          list.reverse().forEach(d => {
            const msg = { ...d, type: 'detection' }
            broadcast(msg)
            if (d.label !== 'normal') {
              window.dispatchEvent(new CustomEvent('apex:detection', { detail: d }))
            }
          })
        } catch (_) {}
      }
      poll()
      pollRef.current = setInterval(poll, 5000)
    }

    function connect() {
      if (dead) return
      try {
        const token = localStorage.getItem('apex_token')
        const url   = `${WS_BASE}/ws/detections${token ? `?token=${encodeURIComponent(token)}` : ''}`
        const ws    = new WebSocket(url)
        wsRef.current = ws

        ws.onopen = () => {
          backoff = 1000
          stopPolling()
        }

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data)
            broadcast(msg)
            if (msg.type === 'detection' && msg.label !== 'normal') {
              window.dispatchEvent(new CustomEvent('apex:detection', { detail: msg }))
            }
          } catch (_) {}
        }

        ws.onerror = () => ws.close()

        ws.onclose = () => {
          if (dead) return
          startPolling()
          retryTimerRef.current = setTimeout(() => {
            backoff = Math.min(backoff * 2, MAX_BACKOFF)
            connect()
          }, backoff)
        }
      } catch (_) {
        if (!dead) startPolling()
      }
    }

    connect()

    return () => {
      dead = true
      clearTimeout(retryTimerRef.current)
      stopPolling()
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [broadcast])

  const subscribe = useCallback((callback) => {
    subscribersRef.current.add(callback)
    return () => subscribersRef.current.delete(callback)
  }, [])

  return (
    <DetectionStreamContext.Provider value={{ subscribe, lastDetections }}>
      {children}
    </DetectionStreamContext.Provider>
  )
}
