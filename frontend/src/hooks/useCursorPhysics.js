import { useEffect, useRef, useState } from 'react'

/**
 * Custom hook for cursor-driven physics interactions
 * Tracks cursor position and provides influence for physics-based animations
 */
export function useCursorPhysics() {
  const [cursorPos, setCursorPos] = useState({ x: 0, y: 0 })
  const [mouseVelocity, setMouseVelocity] = useState({ x: 0, y: 0 })
  const lastPosRef = useRef({ x: 0, y: 0 })
  const velocityDecayRef = useRef(0.95)

  useEffect(() => {
    const handleMouseMove = (e) => {
      const newPos = { x: e.clientX, y: e.clientY }
      const velocity = {
        x: (newPos.x - lastPosRef.current.x) * 0.1,
        y: (newPos.y - lastPosRef.current.y) * 0.1,
      }

      setCursorPos(newPos)
      setMouseVelocity(velocity)
      lastPosRef.current = newPos
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => window.removeEventListener('mousemove', handleMouseMove)
  }, [])

  /**
   * Calculate influence of cursor on element
   * Returns object with transform values for physics-based motion
   */
  const getInfluence = (elementRect, maxDistance = 300, intensity = 1) => {
    if (!elementRect) return { x: 0, y: 0, distance: Infinity }

    const elementCenter = {
      x: elementRect.left + elementRect.width / 2,
      y: elementRect.top + elementRect.height / 2,
    }

    const distance = Math.hypot(
      cursorPos.x - elementCenter.x,
      cursorPos.y - elementCenter.y
    )

    if (distance > maxDistance) {
      return { x: 0, y: 0, distance }
    }

    const influence = Math.max(0, 1 - distance / maxDistance)
    const dirX = (elementCenter.x - cursorPos.x) / distance
    const dirY = (elementCenter.y - cursorPos.y) / distance

    return {
      x: dirX * influence * intensity,
      y: dirY * influence * intensity,
      distance,
      influence,
    }
  }

  return { cursorPos, mouseVelocity, getInfluence }
}
