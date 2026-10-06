import React from 'react'
import ReactDOM from 'react-dom/client'

// Phase 7 — theme tokens FIRST so every downstream sheet can consume the vars.
import './styles/themes.css'
import './styles/typography.css'
import './styles/components.css'
import './styles/transitions.css'
import './styles/print.css'

import App from './App'

// Apply saved theme before first paint (default dark).
const savedTheme = localStorage.getItem('apex-theme') || 'dark'
document.documentElement.dataset.theme = savedTheme

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
