/**
 * Subscribes to the singleton DetectionStreamContext.
 * Every WebSocket message type is forwarded to the callback so callers
 * can filter by msg.type themselves (detection, campaign_update,
 * baseline_alert, scenario_narrative, demo_reset, …).
 *
 * The callback ref pattern means the subscription is created once on
 * mount and is never torn down/re-created on re-renders.
 */
import { useEffect, useRef } from 'react'
import { useDetectionStreamContext } from '../context/DetectionStreamContext'

export function useDetectionStream(onDetection) {
  const ctx         = useDetectionStreamContext()
  const callbackRef = useRef(onDetection)

  // Keep the ref up to date without re-subscribing
  useEffect(() => {
    callbackRef.current = onDetection
  })

  useEffect(() => {
    if (!ctx) return
    const unsubscribe = ctx.subscribe((msg) => callbackRef.current(msg))
    return unsubscribe
  }, [ctx])
}
