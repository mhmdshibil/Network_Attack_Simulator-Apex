import { useEffect, useRef } from 'react'

/**
 * ANIMATION: Custom hook to trigger animations on scroll
 * Observes element visibility and applies animation classes
 */
export function useScrollAnimation(options = {}) {
  const elementRef = useRef(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          // ANIMATION: Add animation class when element enters viewport
          entry.target.style.animation = 'fadeInUp 0.6s ease-out forwards'
          observer.unobserve(entry.target)
        }
      },
      {
        threshold: 0.1,
        ...options,
      }
    )

    if (elementRef.current) {
      observer.observe(elementRef.current)
    }

    return () => {
      if (elementRef.current) {
        observer.unobserve(elementRef.current)
      }
    }
  }, [options])

  return elementRef
}
