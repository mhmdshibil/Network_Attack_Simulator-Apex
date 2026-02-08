import React, { useEffect, useRef } from 'react'
import { useCursorPhysics } from '../hooks/useCursorPhysics'

/**
 * Component that applies cursor-driven physics influence to direct children
 * Elements respond to cursor proximity with subtle position shifts
 */
function PhysicsWrapper({ children }) {
  const { getInfluence } = useCursorPhysics()
  const childrenRefs = useRef([])

  useEffect(() => {
    let frameId = null

    const applyPhysics = () => {
      childrenRefs.current.forEach((ref) => {
        if (!ref) return

        const rect = ref.getBoundingClientRect()
        const influence = getInfluence(rect, 250, 12)

        // Apply smooth translate based on cursor influence
        // Elements are pushed away or attracted slightly
        ref.style.transform = `translate(${influence.x}px, ${influence.y}px)`

        frameId = requestAnimationFrame(applyPhysics)
      })
    }

    frameId = requestAnimationFrame(applyPhysics)

    return () => {
      if (frameId) cancelAnimationFrame(frameId)
    }
  }, [getInfluence])

  return (
    <>
      {React.Children.map(children, (child, index) => (
        <div
          ref={(el) => {
            childrenRefs.current[index] = el
          }}
          style={{
            transition: 'transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
            willChange: 'transform',
          }}
        >
          {child}
        </div>
      ))}
    </>
  )
}

export default PhysicsWrapper
