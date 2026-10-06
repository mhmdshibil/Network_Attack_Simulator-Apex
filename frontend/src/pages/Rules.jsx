/**
 * Rules — Phase 6A: Alert Correlation Rules Engine.
 * Analysts: read-only. Admins: full CRUD + condition builder.
 */
import React, { useState, useEffect, useCallback, useRef, memo } from 'react'
import { Sliders, Plus, Trash2, Edit2, ToggleLeft, ToggleRight, X, ChevronDown } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import './Rules.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('apex_token')
  return fetch(url, {
    ...opts,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(opts.headers || {}) },
  })
}

const ACTIONS    = ['block', 'rate_limit', 'alert', 'escalate']
const FIELDS     = ['attack_type', 'confidence', 'risk_score', 'source_ip', 'target_zone', 'country_code']
const OPERATORS  = ['eq', 'gt', 'lt', 'gte', 'lte', 'in', 'not_in', 'contains']
const ACTION_LABELS = { block: 'Block', rate_limit: 'Rate Limit', alert: 'Alert', escalate: 'Escalate' }
const ACTION_COLORS = {
  block:      'rgba(255,80,80,0.18)',
  rate_limit: 'rgba(255,204,51,0.16)',
  alert:      'rgba(255,255,255,0.10)',
  escalate:   'rgba(255,120,80,0.18)',
}

function conditionSummary(conditions) {
  if (!conditions?.length) return '(no conditions)'
  return conditions.map(c => {
    const v = Array.isArray(c.value) ? `[${c.value.join(', ')}]` : c.value
    return `${c.field} ${c.operator} ${v}`
  }).join(' AND ')
}

const EMPTY_RULE = {
  name: '', description: '', priority: 10, action: 'alert',
  enabled: true, conditions: [],
}
const EMPTY_COND = { field: 'attack_type', operator: 'eq', value: '' }

/* Memoised row (Task 4d) — only re-renders when this rule's data changes. */
const RuleRow = memo(function RuleRow({ r, isAdmin, onEdit, onToggle, onDelete }) {
  return (
    <tr className={r.enabled ? '' : 'rules-row-disabled'}>
      <td className="rules-priority">{r.priority}</td>
      <td>
        <div className="rules-name">{r.name}</div>
        {r.description && <div className="rules-desc">{r.description}</div>}
      </td>
      <td className="rules-conditions">{conditionSummary(r.conditions)}</td>
      <td>
        <span className="rules-action-badge" style={{ background: ACTION_COLORS[r.action] }}>
          {ACTION_LABELS[r.action] || r.action}
        </span>
      </td>
      <td>
        <span className={`rules-status ${r.enabled ? 'on' : 'off'}`}>
          {r.enabled ? 'Enabled' : 'Disabled'}
        </span>
      </td>
      <td className="rules-triggers">
        {r.trigger_count}
        {r.last_triggered && (
          <span className="rules-last-triggered">
            {new Date(r.last_triggered).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </td>
      {isAdmin && (
        <td className="rules-actions-cell">
          <button className="rules-icon-btn" onClick={() => onEdit(r)} title="Edit"><Edit2 size={13} /></button>
          <button className="rules-icon-btn" onClick={() => onToggle(r.id)} title={r.enabled ? 'Disable' : 'Enable'}>
            {r.enabled ? <ToggleRight size={13} /> : <ToggleLeft size={13} />}
          </button>
          <button className="rules-icon-btn rules-delete" onClick={() => onDelete(r.id)} title="Delete"><Trash2 size={13} /></button>
        </td>
      )}
    </tr>
  )
})

export default function Rules() {
  const { role } = useAuth()
  const { showToast } = useToast()
  const isAdmin = role === 'admin' || !role  // when AUTH_ENABLED=false role is undefined
  const [rules, setRules]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [panelOpen, setPanelOpen] = useState(false)
  const [editRule, setEditRule]   = useState(null)   // null = new
  const [form, setForm]           = useState(EMPTY_RULE)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  const load = useCallback(async () => {
    try {
      const r = await authFetch(`${API_BASE}/api/rules`)
      if (r.ok) setRules(await r.json())
    } catch (_) {}
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  function openNew() {
    setEditRule(null)
    setForm({ ...EMPTY_RULE, conditions: [] })
    setError('')
    setPanelOpen(true)
  }

  const openEdit = useCallback((rule) => {
    setEditRule(rule)
    setForm({ ...rule })
    setError('')
    setPanelOpen(true)
  }, [])

  function closePanel() { setPanelOpen(false); setError('') }

  async function handleSave() {
    if (!form.name.trim()) { setError('Name is required'); return }
    setSaving(true); setError('')
    try {
      const url    = editRule ? `${API_BASE}/api/rules/${editRule.id}` : `${API_BASE}/api/rules`
      const method = editRule ? 'PUT' : 'POST'
      const r = await authFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!r.ok) { const j = await r.json(); setError(j.detail || 'Save failed'); setSaving(false); return }
      await load()
      setPanelOpen(false)
      showToast(editRule ? 'Rule updated' : 'Rule created', 'success')
    } catch (e) { setError(String(e)); showToast('Failed to save rule', 'error') }
    setSaving(false)
  }

  const handleDelete = useCallback(async (id) => {
    if (!window.confirm('Delete this rule?')) return
    try {
      await authFetch(`${API_BASE}/api/rules/${id}`, { method: 'DELETE' })
      await load()
      showToast('Rule deleted', 'info')
    } catch { showToast('Failed to delete rule', 'error') }
  }, [load, showToast])

  const handleToggle = useCallback(async (id) => {
    try {
      await authFetch(`${API_BASE}/api/rules/${id}/toggle`, { method: 'POST' })
      await load()
    } catch { showToast('Failed to toggle rule', 'error') }
  }, [load, showToast])

  // ── Condition builder ────────────────────────────────────────────────────

  function addCondition() {
    setForm(f => ({ ...f, conditions: [...f.conditions, { ...EMPTY_COND }] }))
  }

  function updateCondition(i, key, val) {
    setForm(f => {
      const conds = [...f.conditions]
      conds[i] = { ...conds[i], [key]: val }
      return { ...f, conditions: conds }
    })
  }

  function removeCondition(i) {
    setForm(f => ({ ...f, conditions: f.conditions.filter((_, idx) => idx !== i) }))
  }

  if (loading) return <div className="rules-loading">Loading rules…</div>

  return (
    <div className="rules-page">
      <div className="rules-header">
        <div>
          <div className="rules-eyebrow">Automation</div>
          <div className="rules-title"><Sliders size={16} style={{ opacity: 0.6 }} /> Correlation Rules</div>
        </div>
        {isAdmin && (
          <button className="rules-add-btn" onClick={openNew}>
            <Plus size={14} /> Add Rule
          </button>
        )}
      </div>

      {rules.length === 0 ? (
        <div className="rules-empty">No rules defined.</div>
      ) : (
        <table className="rules-table">
          <thead>
            <tr>
              <th>Priority</th>
              <th>Name</th>
              <th>Conditions</th>
              <th>Action</th>
              <th>Status</th>
              <th>Triggers</th>
              {isAdmin && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {rules.map(r => (
              <RuleRow
                key={r.id}
                r={r}
                isAdmin={isAdmin}
                onEdit={openEdit}
                onToggle={handleToggle}
                onDelete={handleDelete}
              />
            ))}
          </tbody>
        </table>
      )}

      {/* ── Add / Edit panel ─────────────────────────────────────────────── */}
      {panelOpen && (
        <div className="rules-panel-overlay" onClick={closePanel}>
          <div className="rules-panel" onClick={e => e.stopPropagation()}>
            <div className="rules-panel-header">
              <span>{editRule ? 'Edit Rule' : 'New Rule'}</span>
              <button className="rules-icon-btn" onClick={closePanel}><X size={14} /></button>
            </div>

            <div className="rules-panel-body">
              <label className="rules-label">Name <span className="rules-req">*</span></label>
              <input className="rules-input" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />

              <label className="rules-label">Description</label>
              <input className="rules-input" value={form.description || ''}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />

              <div className="rules-row2">
                <div>
                  <label className="rules-label">Priority</label>
                  <input type="number" className="rules-input" value={form.priority} min={1}
                    onChange={e => setForm(f => ({ ...f, priority: parseInt(e.target.value) || 1 }))} />
                </div>
                <div>
                  <label className="rules-label">Action</label>
                  <select className="rules-select" value={form.action}
                    onChange={e => setForm(f => ({ ...f, action: e.target.value }))}>
                    {ACTIONS.map(a => <option key={a} value={a}>{ACTION_LABELS[a]}</option>)}
                  </select>
                </div>
              </div>

              <div className="rules-toggle-row">
                <label className="rules-label">Enabled</label>
                <button className="rules-toggle-btn" onClick={() => setForm(f => ({ ...f, enabled: !f.enabled }))}>
                  {form.enabled ? <ToggleRight size={20} style={{ color: 'rgba(255,255,255,0.8)' }} />
                                : <ToggleLeft  size={20} style={{ color: 'rgba(255,255,255,0.35)' }} />}
                </button>
              </div>

              <div className="rules-cond-header">
                <span className="rules-label" style={{ marginBottom: 0 }}>Conditions (AND)</span>
                <button className="rules-add-cond-btn" onClick={addCondition}><Plus size={12} /> Add</button>
              </div>

              {form.conditions.map((c, i) => (
                <div key={i} className="rules-cond-row">
                  <select className="rules-select rules-cond-select" value={c.field}
                    onChange={e => updateCondition(i, 'field', e.target.value)}>
                    {FIELDS.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                  <select className="rules-select rules-cond-select" value={c.operator}
                    onChange={e => updateCondition(i, 'operator', e.target.value)}>
                    {OPERATORS.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                  <input className="rules-input rules-cond-val" placeholder="value"
                    value={Array.isArray(c.value) ? c.value.join(',') : c.value}
                    onChange={e => {
                      const raw = e.target.value
                      const val = ['in', 'not_in'].includes(c.operator)
                        ? raw.split(',').map(s => s.trim()).filter(Boolean)
                        : raw
                      updateCondition(i, 'value', val)
                    }} />
                  <button className="rules-icon-btn rules-delete" onClick={() => removeCondition(i)}><X size={12} /></button>
                </div>
              ))}

              {form.conditions.length === 0 && (
                <div className="rules-cond-empty">No conditions — rule will never match.</div>
              )}

              {error && <div className="rules-error">{error}</div>}
            </div>

            <div className="rules-panel-footer">
              <button className="rules-cancel-btn" onClick={closePanel}>Cancel</button>
              <button className="rules-save-btn" onClick={handleSave} disabled={saving}>
                {saving ? 'Saving…' : 'Save Rule'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
