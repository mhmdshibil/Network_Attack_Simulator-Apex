/**
 * Webhooks — Phase 6C: Outbound webhook integrations.
 * Admin-only CRUD. Shows delivery stats per webhook.
 */
import React, { useState, useEffect, useCallback, memo } from 'react'
import { Webhook, Plus, Edit2, Trash2, ToggleLeft, ToggleRight, X, Eye, EyeOff, Zap } from 'lucide-react'
import { useToast } from '../context/ToastContext'
import './Webhooks.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('apex_token')
  return fetch(url, {
    ...opts,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  })
}

const EVENT_OPTIONS = [
  { value: 'detection',       label: 'Detection' },
  { value: 'campaign',        label: 'Campaign' },
  { value: 'baseline_alert',  label: 'Baseline Alert' },
  { value: 'triage_resolved', label: 'Triage Resolved' },
]

function timeAgo(ts) {
  if (!ts) return '—'
  const s = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
  if (s < 60)   return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

const EMPTY_FORM = { name: '', url: '', events: [], secret: '', enabled: true }

/* Memoised webhook card (Task 4d) — only re-renders when its data/test result changes. */
const WebhookCard = memo(function WebhookCard({ wh, testMsg, onTest, onEdit, onToggle, onDelete }) {
  return (
    <div className={`wh-card ${wh.enabled ? '' : 'wh-card-disabled'}`}>
      <div className="wh-card-head">
        <div className="wh-card-status-dot" style={{ background: wh.enabled ? '#6fff8f' : 'rgba(255,255,255,0.2)' }} />
        <div className="wh-card-name">{wh.name}</div>
        <div className="wh-card-actions">
          <button className="wh-icon-btn" onClick={() => onTest(wh.id)} title="Test"><Zap size={13} /></button>
          <button className="wh-icon-btn" onClick={() => onEdit(wh)} title="Edit"><Edit2 size={13} /></button>
          <button className="wh-icon-btn" onClick={() => onToggle(wh.id)} title={wh.enabled ? 'Disable' : 'Enable'}>
            {wh.enabled ? <ToggleRight size={13} /> : <ToggleLeft size={13} />}
          </button>
          <button className="wh-icon-btn wh-delete" onClick={() => onDelete(wh.id)} title="Delete"><Trash2 size={13} /></button>
        </div>
      </div>
      <div className="wh-card-url">{wh.url}</div>
      <div className="wh-card-events">
        {wh.events.map(e => (
          <span key={e} className="wh-event-tag">{e.replace(/_/g, ' ')}</span>
        ))}
      </div>
      <div className="wh-card-stats">
        <span>{wh.total_deliveries} deliveries</span>
        {wh.failed_deliveries > 0 && <span className="wh-stat-fail">, {wh.failed_deliveries} failed</span>}
        <span style={{ marginLeft: 'auto' }}>Last: {timeAgo(wh.last_triggered)}</span>
      </div>
      {testMsg && (
        <div className={`wh-test-result ${testMsg.startsWith('✓') ? 'ok' : 'fail'}`}>{testMsg}</div>
      )}
    </div>
  )
})

export default function Webhooks() {
  const { showToast } = useToast()
  const [webhooks,   setWebhooks]   = useState([])
  const [loading,    setLoading]    = useState(true)
  const [panelOpen,  setPanelOpen]  = useState(false)
  const [editWh,     setEditWh]     = useState(null)
  const [form,       setForm]       = useState(EMPTY_FORM)
  const [showSecret, setShowSecret] = useState(false)
  const [saving,     setSaving]     = useState(false)
  const [error,      setError]      = useState('')
  const [testResult, setTestResult] = useState({})  // id → result string

  const load = useCallback(async () => {
    try {
      const r = await authFetch(`${API_BASE}/api/webhooks`)
      if (r.ok) setWebhooks(await r.json())
    } catch (_) {}
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  function openNew() {
    setEditWh(null); setForm({ ...EMPTY_FORM, events: [] }); setError(''); setShowSecret(false); setPanelOpen(true)
  }
  const openEdit = useCallback((wh) => {
    setEditWh(wh); setForm({ name: wh.name, url: wh.url, events: [...wh.events], secret: '', enabled: wh.enabled })
    setError(''); setShowSecret(false); setPanelOpen(true)
  }, [])
  function closePanel() { setPanelOpen(false); setError('') }

  function toggleEvent(val) {
    setForm(f => ({
      ...f,
      events: f.events.includes(val) ? f.events.filter(e => e !== val) : [...f.events, val],
    }))
  }

  async function handleSave() {
    if (!form.name.trim()) { setError('Name is required'); return }
    if (!form.url.trim())  { setError('URL is required'); return }
    setSaving(true); setError('')
    const payload = { ...form }
    if (!payload.secret) delete payload.secret  // don't overwrite if not changed
    try {
      const url    = editWh ? `${API_BASE}/api/webhooks/${editWh.id}` : `${API_BASE}/api/webhooks`
      const method = editWh ? 'PUT' : 'POST'
      const r = await authFetch(url, {
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      })
      if (!r.ok) { const j = await r.json(); setError(j.detail || 'Save failed'); setSaving(false); return }
      await load(); setPanelOpen(false)
      showToast(editWh ? 'Webhook updated' : 'Webhook created', 'success')
    } catch (e) { setError(String(e)); showToast('Failed to save webhook', 'error') }
    setSaving(false)
  }

  const handleDelete = useCallback(async (id) => {
    if (!window.confirm('Delete this webhook?')) return
    try {
      await authFetch(`${API_BASE}/api/webhooks/${id}`, { method: 'DELETE' })
      await load()
      showToast('Webhook deleted', 'info')
    } catch { showToast('Failed to delete webhook', 'error') }
  }, [load, showToast])

  const handleToggle = useCallback(async (id) => {
    try {
      await authFetch(`${API_BASE}/api/webhooks/${id}/toggle`, { method: 'POST' })
      await load()
    } catch { showToast('Failed to toggle webhook', 'error') }
  }, [load, showToast])

  const handleTest = useCallback(async (id) => {
    setTestResult(r => ({ ...r, [id]: 'testing…' }))
    try {
      const r = await authFetch(`${API_BASE}/api/webhooks/${id}/test`, { method: 'POST' })
      const j = await r.json()
      const ok = j.status === 'success'
      const msg = ok
        ? `✓ Delivered (${j.response_code} OK)`
        : `✗ Failed (${j.status}${j.response_code ? ' · ' + j.response_code : ''})`
      setTestResult(r => ({ ...r, [id]: msg }))
      showToast(ok ? 'Webhook delivered' : 'Webhook test failed', ok ? 'success' : 'error')
    } catch (e) {
      setTestResult(r => ({ ...r, [id]: '✗ Network error' }))
      showToast('Webhook test failed', 'error')
    }
    setTimeout(() => setTestResult(r => { const next = { ...r }; delete next[id]; return next }), 5000)
  }, [showToast])

  if (loading) return <div className="wh-loading">Loading webhooks…</div>

  return (
    <div className="wh-page">
      <div className="wh-header">
        <div>
          <div className="wh-eyebrow">Integrations</div>
          <div className="wh-title"><Webhook size={16} style={{ opacity: 0.6 }} /> Webhooks</div>
        </div>
        <button className="wh-add-btn" onClick={openNew}><Plus size={14} /> Add Webhook</button>
      </div>

      {webhooks.length === 0 ? (
        <div className="wh-empty">No webhooks configured. Add one to receive event notifications.</div>
      ) : (
        <div className="wh-cards">
          {webhooks.map(wh => (
            <WebhookCard
              key={wh.id}
              wh={wh}
              testMsg={testResult[wh.id]}
              onTest={handleTest}
              onEdit={openEdit}
              onToggle={handleToggle}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* ── Panel ─────────────────────────────────────────────────────── */}
      {panelOpen && (
        <div className="wh-panel-overlay" onClick={closePanel}>
          <div className="wh-panel" onClick={e => e.stopPropagation()}>
            <div className="wh-panel-header">
              <span>{editWh ? 'Edit Webhook' : 'New Webhook'}</span>
              <button className="wh-icon-btn" onClick={closePanel}><X size={14} /></button>
            </div>
            <div className="wh-panel-body">
              <label className="wh-label">Name <span className="wh-req">*</span></label>
              <input className="wh-input" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />

              <label className="wh-label">URL <span className="wh-req">*</span></label>
              <input className="wh-input" type="url" placeholder="https://..."
                value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />

              <label className="wh-label">Events</label>
              <div className="wh-events-group">
                {EVENT_OPTIONS.map(opt => (
                  <label key={opt.value} className="wh-checkbox-row">
                    <input type="checkbox" checked={form.events.includes(opt.value)}
                      onChange={() => toggleEvent(opt.value)} />
                    {opt.label}
                  </label>
                ))}
              </div>

              <label className="wh-label">Secret (HMAC-SHA256 signing)</label>
              <div className="wh-secret-row">
                <input className="wh-input wh-secret-input"
                  type={showSecret ? 'text' : 'password'}
                  placeholder={editWh ? '(unchanged)' : 'optional'}
                  value={form.secret}
                  onChange={e => setForm(f => ({ ...f, secret: e.target.value }))} />
                <button className="wh-icon-btn" onClick={() => setShowSecret(s => !s)}>
                  {showSecret ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
              </div>

              <div className="wh-toggle-row">
                <span className="wh-label" style={{ marginBottom: 0 }}>Enabled</span>
                <button className="wh-toggle-btn" onClick={() => setForm(f => ({ ...f, enabled: !f.enabled }))}>
                  {form.enabled
                    ? <ToggleRight size={20} style={{ color: 'rgba(255,255,255,0.8)' }} />
                    : <ToggleLeft  size={20} style={{ color: 'rgba(255,255,255,0.35)' }} />}
                </button>
              </div>

              {error && <div className="wh-error">{error}</div>}
            </div>
            <div className="wh-panel-footer">
              <button className="wh-cancel-btn" onClick={closePanel}>Cancel</button>
              <button className="wh-save-btn" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save Webhook'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
