import { useState, useEffect, useCallback } from 'react'

/**
 * useDarkMode — Phase 7 Task 1.
 * Theme is driven by document.documentElement.dataset.theme ("dark" | "light")
 * and persisted under localStorage "apex-theme". main.jsx applies the saved
 * theme before first paint; this hook keeps React state in sync and exposes a
 * toggle. Same { isDark, toggle } API the Sidebar already consumes.
 */
export function useDarkMode() {
  const getTheme = () =>
    document.documentElement.dataset.theme ||
    localStorage.getItem('apex-theme') ||
    'dark'

  const [theme, setTheme] = useState(getTheme)

  // Reflect any external theme change (e.g. another tab) into local state.
  useEffect(() => {
    const observer = new MutationObserver(() => {
      const current = document.documentElement.dataset.theme || 'dark'
      setTheme(prev => (prev === current ? prev : current))
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  const toggle = useCallback(() => {
    const next = (document.documentElement.dataset.theme || 'dark') === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    localStorage.setItem('apex-theme', next)
    setTheme(next)
  }, [])

  return { isDark: theme === 'dark', theme, toggle }
}
