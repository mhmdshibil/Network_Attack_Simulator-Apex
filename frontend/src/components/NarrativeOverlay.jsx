import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Square } from 'lucide-react'
import { fetchScenarioStatus, stopScenario } from '../api/api'
import { useDetectionStream } from '../hooks/useDetectionStream'
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

  // Poll at 10 s — WS handler below gives immediate updates when scenario fires
  useEffect(() => {
    const poll = async () => {
      try {
        const s = await fetchScenarioStatus()
        setStatus(s)
      } catch { }
    }
    const delay = Math.random() * 2000
    let iv
    const t = setTimeout(() => {
      poll()
      iv = setInterval(poll, 10000)
    }, delay)
    return () => { clearTimeout(t); clearInterval(iv) }
  }, [])

  // Real-time updates from the shared singleton WebSocket
  useDetectionStream(useCallback((msg) => {
    if (msg.type === 'scenario_narrative') {
      setStatus(prev => ({
        ...prev,
        is_running: !msg.complete,
        current_act: msg.act      ?? prev.current_act,
        act_name:    msg.act_name ?? prev.act_name,
        progress:    msg.progress ?? prev.progress,
        narrative_text: msg.text  ?? prev.narrative_text,
      }))
    }
    if (msg.type === 'demo_reset') {
      setStatus({ is_running: false, current_act: 0, act_name: '', progress: 0, narrative_text: '' })
    }
  }, []))

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
