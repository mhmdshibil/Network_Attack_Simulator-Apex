import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Square } from 'lucide-react'
import { fetchScenarioStatus, stopScenario, API_BASE } from '../api/api'
import './NarrativeOverlay.css'

const TOTAL_ACTS = 5

function useTypewriter(text, msPerChar = 30) {
  const [displayed, setDisplayed] = useState(text)
  const prevTextRef = useRef(text)

  useEffect(() => {
    if (text === prevTextRef.current) return
    prevTextRef.current = text
    let i = 0
    setDisplayed('')
    const iv = setInterval(() => {
      i += 1
      setDisplayed(text.slice(0, i))
      if (i >= text.length) clearInterval(iv)
    }, msPerChar)
    return () => clearInterval(iv)
  }, [text, msPerChar])

  return displayed
}

function NarrativeOverlay() {
  const [status, setStatus] = useState({
    is_running: false, current_act: 0, act_name: '', progress: 0, narrative_text: '',
  })
  const [stopping, setStopping] = useState(false)

  const displayedText = useTypewriter(status.narrative_text, 30)

  // Poll status every 2 seconds
  useEffect(() => {
    const poll = async () => {
      try {
        const s = await fetchScenarioStatus()
        setStatus(s)
      } catch { }
    }
    poll()
    const iv = setInterval(poll, 2000)
    return () => clearInterval(iv)
  }, [])

  // WebSocket: listen for scenario_narrative messages for immediate updates
  useEffect(() => {
    const wsUrl = API_BASE.replace(/^http/, 'ws') + '/ws/detections'
    let ws
    let dead = false

    const connect = () => {
      if (dead) return
      ws = new WebSocket(wsUrl)
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'scenario_narrative') {
            setStatus(prev => ({
              ...prev,
              is_running: !msg.complete,
              current_act: msg.act ?? prev.current_act,
              act_name: msg.act_name ?? prev.act_name,
              progress: msg.progress ?? prev.progress,
              narrative_text: msg.text ?? prev.narrative_text,
            }))
          }
          if (msg.type === 'demo_reset') {
            setStatus({ is_running: false, current_act: 0, act_name: '', progress: 0, narrative_text: '' })
          }
        } catch { }
      }
      ws.onclose = () => { if (!dead) setTimeout(connect, 3000) }
      ws.onerror = () => { ws.close() }
    }

    connect()
    return () => { dead = true; ws?.close() }
  }, [])

  const handleStop = useCallback(async () => {
    if (stopping) return
    setStopping(true)
    try { await stopScenario() } catch { }
    finally { setStopping(false) }
  }, [stopping])

  if (!status.is_running) return null

  return (
    <div className="narrative-overlay" role="status" aria-live="polite">
      <div className="narrative-header">
        <span className="narrative-header-pulse" />
        SCENARIO ACTIVE
      </div>

      <div className="narrative-act">
        ACT {status.current_act} OF {TOTAL_ACTS} — {status.act_name || '…'}
      </div>

      <div className="narrative-text">{displayedText}</div>

      <div className="narrative-progress-track">
        <div className="narrative-progress-fill" style={{ width: `${status.progress}%` }} />
      </div>

      <button className="narrative-stop-btn" onClick={handleStop} disabled={stopping}>
        <Square size={9} />
        {stopping ? 'Stopping…' : 'Stop Scenario'}
      </button>
    </div>
  )
}

export default NarrativeOverlay
