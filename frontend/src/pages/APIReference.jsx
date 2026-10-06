/**
 * APIReference — Phase 7 Task 5b.
 * Collapsible endpoint catalogue grouped by domain. Each section is memoised
 * (Task 4d) so opening one doesn't re-render the others.
 */
import React, { useState, useCallback, memo } from 'react'
import { Code2, ChevronDown, ExternalLink } from 'lucide-react'
import { API_BASE } from '../api/api'
import './APIReference.css'

const GROUPS = [
  {
    name: 'Detection',
    endpoints: [
      ['GET',  '/api/detections',            'List recent detections',                 'analyst'],
      ['POST', '/api/detections',            'Ingest a feature window (sensor agent)', 'analyst'],
      ['GET',  '/api/explain',               'SHAP explanation for a detection',       'analyst'],
      ['GET',  '/api/explain/summary',       'Global SHAP + Gini feature importance',  'analyst'],
    ],
  },
  {
    name: 'Analytics',
    endpoints: [
      ['GET', '/api/analytics/timeline',      'Traffic timeline (windowed)',  'analyst'],
      ['GET', '/api/analytics/top_attackers', 'Top attacking IPs',            'analyst'],
      ['GET', '/api/analytics/attack_trends', 'Attack-type trend series',     'analyst'],
      ['GET', '/api/analytics/risk',          'Risk distribution',            'analyst'],
      ['GET', '/api/metrics',                 'Core platform metrics',        'analyst'],
      ['GET', '/api/alerts',                  'Recent alert feed',            'analyst'],
    ],
  },
  {
    name: 'Triage',
    endpoints: [
      ['GET',   '/api/triage',          'List triage cases (filterable)', 'analyst'],
      ['GET',   '/api/triage/{id}',     'Case detail + notes',            'analyst'],
      ['PATCH', '/api/triage/{id}',     'Update / acknowledge a case',    'analyst'],
      ['GET',   '/api/triage/stats',    'Triage aggregate stats',         'analyst'],
    ],
  },
  {
    name: 'Campaigns',
    endpoints: [
      ['GET',  '/api/campaigns',             'List correlated campaigns',    'analyst'],
      ['GET',  '/api/campaigns/active',      'Active campaigns only',        'analyst'],
      ['GET',  '/api/campaigns/stats',       'Campaign aggregate stats',     'analyst'],
      ['GET',  '/api/campaigns/{id}',        'Campaign detail + timeline',   'analyst'],
      ['POST', '/api/campaigns/{id}/resolve','Manually resolve a campaign',  'analyst'],
    ],
  },
  {
    name: 'Intelligence',
    endpoints: [
      ['GET', '/api/threat-intel/{ip}',   'IP reputation lookup',        'analyst'],
      ['GET', '/api/threat-intel/stats',  'Threat-intel config status',  'analyst'],
      ['GET', '/api/cve/stats',           'CISA KEV feed stats',         'analyst'],
      ['GET', '/api/cve/recent',          'Recently added CVEs',         'analyst'],
      ['GET', '/api/cve/match/{type}',    'CVEs matching an attack type', 'analyst'],
      ['POST','/api/cve/refresh',         'Force a KEV re-fetch',        'analyst'],
    ],
  },
  {
    name: 'GeoIP',
    endpoints: [
      ['GET', '/api/geo/{ip}',      'Geolocate an IP',        'analyst'],
      ['GET', '/api/geo/summary',   'Geo attack summary',     'analyst'],
      ['GET', '/api/geo/attackers', 'Geolocated attackers',   'analyst'],
    ],
  },
  {
    name: 'Baseline',
    endpoints: [
      ['GET',  '/api/baseline/status',     'Learning / active status',     'analyst'],
      ['GET',  '/api/baseline/stats/{h}',  'Per-hour feature stats',       'analyst'],
      ['GET',  '/api/baseline/alerts',     'Baseline deviation alerts',    'analyst'],
      ['GET',  '/api/baseline/chart',      '24-hour mean/std series',      'analyst'],
      ['POST', '/api/baseline/reset',      'Clear all baseline data',      'admin'],
    ],
  },
  {
    name: 'Rules',
    endpoints: [
      ['GET',    '/api/rules',            'List correlation rules',        'analyst'],
      ['POST',   '/api/rules',            'Create a rule',                 'admin'],
      ['PUT',    '/api/rules/{id}',       'Update a rule',                 'admin'],
      ['DELETE', '/api/rules/{id}',       'Delete a rule',                 'admin'],
      ['POST',   '/api/rules/{id}/toggle','Enable / disable a rule',       'admin'],
      ['POST',   '/api/rules/evaluate',   'Dry-run a sample detection',    'analyst'],
    ],
  },
  {
    name: 'Webhooks',
    endpoints: [
      ['GET',    '/api/webhooks',              'List webhooks',           'admin'],
      ['POST',   '/api/webhooks',              'Create a webhook',        'admin'],
      ['PUT',    '/api/webhooks/{id}',         'Update a webhook',        'admin'],
      ['DELETE', '/api/webhooks/{id}',         'Delete a webhook',        'admin'],
      ['POST',   '/api/webhooks/{id}/test',    'Send a test payload',     'admin'],
      ['GET',    '/api/webhooks/{id}/deliveries','Last 50 deliveries',    'admin'],
      ['POST',   '/api/webhooks/{id}/toggle',  'Enable / disable',        'admin'],
    ],
  },
  {
    name: 'Reports',
    endpoints: [
      ['GET', '/api/reports/weekly',     'Weekly threat PDF',       'analyst'],
      ['GET', '/api/reports/compliance', 'ISO 27001 compliance PDF','analyst'],
    ],
  },
  {
    name: 'Auth & 2FA',
    endpoints: [
      ['POST', '/api/auth/token',        'OAuth2 login → JWT',          'public'],
      ['GET',  '/api/auth/status',       'Server feature flags',        'public'],
      ['POST', '/api/auth/2fa/setup',    'Generate TOTP secret + QR',   'analyst'],
      ['POST', '/api/auth/2fa/activate', 'Activate 2FA',                'analyst'],
      ['POST', '/api/auth/2fa/verify',   'Verify code → full JWT',      'temp-token'],
      ['POST', '/api/auth/2fa/disable',  'Disable 2FA',                 'analyst'],
      ['GET',  '/api/auth/2fa/status',   'Per-user 2FA status',         'analyst'],
    ],
  },
  {
    name: 'System & Admin',
    endpoints: [
      ['GET',  '/api/health',             'Health check',            'public'],
      ['GET',  '/api/system/overview',    'System overview',         'analyst'],
      ['GET',  '/api/system/blocked_ips', 'Blocked IP list',         'analyst'],
      ['POST', '/api/admin/reset-demo',   'Reset to clean state',    'admin'],
      ['GET',  '/api/schedule/status',    'Scheduled replay status', 'analyst'],
      ['POST', '/api/schedule/set',       'Set replay schedule',     'admin'],
    ],
  },
  {
    name: 'Demo & NLQ',
    endpoints: [
      ['POST', '/api/demo/enable',   'Enable demo scheduler',       'analyst'],
      ['POST', '/api/demo/trigger',  'Fire a manual attack',        'analyst'],
      ['POST', '/api/scenario/start','Start the 5-act scenario',    'analyst'],
      ['POST', '/api/nlq',           'Natural-language query',      'analyst'],
      ['POST', '/api/push/subscribe','Register a push subscription','analyst'],
      ['GET',  '/api/push/vapid-public-key','Public VAPID key',     'public'],
    ],
  },
]

const METHOD_CLASS = {
  GET: 'm-get', POST: 'm-post', PUT: 'm-put', PATCH: 'm-patch', DELETE: 'm-delete',
}

const AUTH_CLASS = {
  public: 'a-public', analyst: 'a-analyst', admin: 'a-admin', 'temp-token': 'a-temp',
}

const Section = memo(function Section({ group, open, onToggle }) {
  return (
    <div className="apiref-section">
      <button className="apiref-section-head" onClick={onToggle}>
        <ChevronDown size={14} className={`apiref-chevron ${open ? 'open' : ''}`} />
        <span className="apiref-section-name">{group.name}</span>
        <span className="apiref-section-count">{group.endpoints.length}</span>
      </button>
      {open && (
        <div className="apiref-endpoints">
          {group.endpoints.map(([method, path, desc, auth]) => (
            <div key={method + path} className="apiref-endpoint">
              <span className={`apiref-method ${METHOD_CLASS[method] || ''}`}>{method}</span>
              <code className="apiref-path">{path}</code>
              <span className="apiref-desc">{desc}</span>
              <span className={`apiref-auth ${AUTH_CLASS[auth] || ''}`}>{auth}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
})

export default function APIReference() {
  const [openSet, setOpenSet] = useState(() => new Set(['Detection']))

  const toggle = useCallback((name) => {
    setOpenSet(prev => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }, [])

  const total = GROUPS.reduce((n, g) => n + g.endpoints.length, 0)

  return (
    <div className="apiref-page">
      <div className="apiref-header">
        <div>
          <div className="page-subtitle">Developer</div>
          <div className="page-title"><Code2 size={18} style={{ opacity: 0.6, verticalAlign: '-3px', marginRight: 8 }} />API Reference</div>
        </div>
        <a className="apiref-swagger" href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
          Open Swagger UI <ExternalLink size={13} />
        </a>
      </div>

      <p className="apiref-intro">
        {total} REST endpoints across {GROUPS.length} domains. Auth levels: <b>public</b> (no token),
        <b> analyst</b> (JWT, analyst or admin), <b>admin</b> (JWT, admin only). Auth is enforced only
        when <code>AUTH_ENABLED=true</code>.
      </p>

      {GROUPS.map(group => (
        <Section
          key={group.name}
          group={group}
          open={openSet.has(group.name)}
          onToggle={() => toggle(group.name)}
        />
      ))}
    </div>
  )
}
