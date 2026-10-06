/**
 * Toast — Phase 7 Task 3f.
 * A single toast card. Memoised so re-rendering the stack doesn't touch
 * unrelated toasts.
 */
import React from 'react'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'
import './Toast.css'

const ICONS = {
  success: CheckCircle,
  error:   AlertCircle,
  info:    Info,
}

const Toast = React.memo(function Toast({ message, type = 'info', onDismiss }) {
  const Icon = ICONS[type] || Info
  return (
    <div className={`toast toast-${type}`} role="status">
      <Icon size={15} className="toast-icon" />
      <span className="toast-msg">{message}</span>
      <button className="toast-close" onClick={onDismiss} aria-label="Dismiss">
        <X size={13} />
      </button>
    </div>
  )
})

export default Toast
