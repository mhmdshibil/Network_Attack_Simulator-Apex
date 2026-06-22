import { useEffect, useRef, useState } from 'react'

export function useCountUp(target, duration = 900) {
  const [display, setDisplay] = useState(target)
  const prevRef = useRef(target)
  const frameRef = useRef(null)

  useEffect(() => {
    const prefersReduced = typeof window !== 'undefined'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const from = typeof prevRef.current === 'number' ? prevRef.current : null
    const to   = typeof target === 'number' ? target : null

    cancelAnimationFrame(frameRef.current)

    if (to === null) {
      setDisplay(target)
      prevRef.current = target
      return
    }

    if (from === null || from === to || prefersReduced) {
      setDisplay(target)
      prevRef.current = target
      return
    }

    const start = performance.now()
    const animate = (now) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(Math.round(from + (to - from) * eased))
      if (t < 1) {
        frameRef.current = requestAnimationFrame(animate)
      } else {
        setDisplay(to)
        prevRef.current = to
      }
    }
    frameRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frameRef.current)
  }, [target, duration])

  return display
}
