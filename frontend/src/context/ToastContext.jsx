/**
 * ToastContext — Phase 7 Task 3f + 4e.
 *
 * Provides a stable `showToast(message, type)` via useToast(). The toast LIST
 * lives inside the <Toaster> renderer and is driven by a ref-based subscriber
 * set, so calling showToast never re-renders the consumers of useToast() — only
 * the Toaster itself updates. (Task 4e requirement.)
 */
import React, { createContext, useContext, useRef, useCallback, useState, useEffect } from 'react'
import Toast from '../components/Toast'

const ToastContext = createContext(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  // Safe no-op if provider is missing (keeps components decoupled).
  return ctx || { showToast: () => {} }
}

export function ToastProvider({ children }) {
  // Subscribers (the Toaster) register here. showToast notifies them.
  const listenersRef = useRef(new Set())

  const showToast = useCallback((message, type = 'info') => {
    const toast = { id: Date.now() + Math.random(), message, type }
    listenersRef.current.forEach(fn => fn(toast))
  }, [])

  const subscribe = useCallback((fn) => {
    listenersRef.current.add(fn)
    return () => listenersRef.current.delete(fn)
  }, [])

  // ctxValue is stable across renders → consumers never re-render on toast.
  const ctxValue = useRef({ showToast }).current

  return (
    <ToastContext.Provider value={ctxValue}>
      {children}
      <Toaster subscribe={subscribe} />
    </ToastContext.Provider>
  )
}

const MAX_TOASTS = 4
const AUTO_DISMISS_MS = 4000

function Toaster({ subscribe }) {
  const [toasts, setToasts] = useState([])
  const timersRef = useRef({})

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
    if (timersRef.current[id]) {
      clearTimeout(timersRef.current[id])
      delete timersRef.current[id]
    }
  }, [])

  useEffect(() => {
    const unsub = subscribe((toast) => {
      setToasts(prev => [...prev, toast].slice(-MAX_TOASTS))
      timersRef.current[toast.id] = setTimeout(() => dismiss(toast.id), AUTO_DISMISS_MS)
    })
    return unsub
  }, [subscribe, dismiss])

  // Clean up any pending timers on unmount.
  useEffect(() => () => {
    Object.values(timersRef.current).forEach(clearTimeout)
  }, [])

  if (toasts.length === 0) return null

  return (
    <div className="toast-stack">
      {toasts.map(t => (
        <Toast key={t.id} message={t.message} type={t.type} onDismiss={() => dismiss(t.id)} />
      ))}
    </div>
  )
}
