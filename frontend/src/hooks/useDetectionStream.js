/**
 * Phase 8 — WebSocket hook with polling fallback.
 * Phase 11 — Passes JWT token as query param for WS auth.
 *
 * Connects to /ws/detections. On each "detection" message the callback fires.
 * If the WebSocket is unavailable or disconnects, falls back to polling
 * the /api/detections endpoint every `pollInterval` ms.
 */
import { useEffect, useRef, useCallback } from 'react'

const WS_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000')
  .replace(/^http/, 'ws')

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function wsUrl() {
  const token = localStorage.getItem('apex_token')
  const base = `${WS_BASE}/ws/detections`
  return token ? `${base}?token=${encodeURIComponent(token)}` : base
}

export function useDetectionStream(onDetection, { pollInterval = 5000 } = {}) {
  const wsRef = useRef(null)
  const pollRef = useRef(null)
  const fallbackActive = useRef(false)

  const startPolling = useCallback(() => {
    if (fallbackActive.current) return
    fallbackActive.current = true
    const token = localStorage.getItem('apex_token')
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/detections?limit=20`, { headers })
        if (res.status === 401) return
        const data = await res.json()
        const list = Array.isArray(data) ? data : []
        list.reverse().forEach(d => {
          onDetection(d)
          if (d.label !== 'normal') {
            window.dispatchEvent(new CustomEvent('apex:detection', { detail: d }))
          }
        })
      } catch (_) {}
    }
    poll()
    pollRef.current = setInterval(poll, pollInterval)
  }, [onDetection, pollInterval])

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current)
    fallbackActive.current = false
  }, [])

  useEffect(() => {
    let reconnectTimer = null

    function connect() {
      try {
        const ws = new WebSocket(wsUrl())
        wsRef.current = ws

        ws.onopen = () => {
          stopPolling()
        }

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data)
            if (msg.type === 'detection') {
              onDetection(msg)
              // Fire global event so ParticleBackground can react to real detections
              if (msg.label !== 'normal') {
                window.dispatchEvent(new CustomEvent('apex:detection', { detail: msg }))
              }
            }
          } catch (_) {}
        }

        ws.onerror = () => {
          ws.close()
        }

        ws.onclose = () => {
          startPolling()
          reconnectTimer = setTimeout(connect, 8000)
        }
      } catch (_) {
        startPolling()
      }
    }

    connect()

    return () => {
      clearTimeout(reconnectTimer)
      stopPolling()
      if (wsRef.current) wsRef.current.close()
    }
  }, [onDetection, startPolling, stopPolling])
}
