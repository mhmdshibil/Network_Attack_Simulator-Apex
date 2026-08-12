/**
 * Phase 8 — WebSocket hook with polling fallback.
 *
 * Connects to /ws/detections. On each "detection" message the callback fires.
 * If the WebSocket is unavailable or disconnects, falls back to polling
 * the /api/detections endpoint every `pollInterval` ms.
 */
import { useEffect, useRef, useCallback } from 'react'

const WS_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000')
  .replace(/^http/, 'ws')

export function useDetectionStream(onDetection, { pollInterval = 5000 } = {}) {
  const wsRef = useRef(null)
  const pollRef = useRef(null)
  const fallbackActive = useRef(false)

  const startPolling = useCallback(() => {
    if (fallbackActive.current) return
    fallbackActive.current = true
    const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/detections?limit=20`)
        const data = await res.json()
        const list = Array.isArray(data) ? data : []
        list.reverse().forEach(d => onDetection(d))
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
        const ws = new WebSocket(`${WS_BASE}/ws/detections`)
        wsRef.current = ws

        ws.onopen = () => {
          stopPolling()
        }

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data)
            if (msg.type === 'detection') onDetection(msg)
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
