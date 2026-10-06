import React, { lazy, Suspense } from 'react'

// Eager — likely first-visit pages
import Dashboard       from './Dashboard'
import LiveTraffic     from './LiveTraffic'
import DetectedAttacks from './DetectedAttacks'
import Triage          from './Triage'
import RiskAnalysis    from './RiskAnalysis'
import AttackAnalytics from './AttackAnalytics'
import BlockedIPs      from './BlockedIPs'
import NetworkMap      from './NetworkMap'

// Lazy — heavy pages that don't need to load until navigated to
const GeoMap       = lazy(() => import('./GeoMap'))
const Campaigns    = lazy(() => import('./Campaigns'))
const Compliance   = lazy(() => import('./Compliance'))
const Baseline     = lazy(() => import('./Baseline'))
const ModelInsights = lazy(() => import('./ModelInsights'))
const Roadmap      = lazy(() => import('./Roadmap'))
const Rules        = lazy(() => import('./Rules'))
const Webhooks     = lazy(() => import('./Webhooks'))
const APIReference = lazy(() => import('./APIReference'))

const sections = {
  'dashboard':          Dashboard,
  'live-traffic':       LiveTraffic,
  'detected-attacks':   DetectedAttacks,
  'risk-analysis':      RiskAnalysis,
  'attack-analytics':   AttackAnalytics,
  'blocked-ips':        BlockedIPs,
  'network-map':        NetworkMap,
  'geo-map':            GeoMap,
  'campaigns':          Campaigns,
  'baseline':           Baseline,
  'triage':             Triage,
  'compliance':         Compliance,
  'model-insights':     ModelInsights,
  'roadmap':            Roadmap,
  'rules':              Rules,
  'webhooks':           Webhooks,
  'api-docs':           APIReference,
}

const LoadingFallback = () => (
  <div style={{ color: '#888', padding: '40px', textAlign: 'center',
                fontFamily: "'IBM Plex Mono', monospace", fontSize: '12px' }}>
    Loading…
  </div>
)

function UnifiedDashboard({ activeSection }) {
  const Component = sections[activeSection] ?? Dashboard
  return (
    <div className="unified-dashboard">
      {/* key={activeSection} remounts on nav → re-triggers the page-enter fade */}
      <section key={activeSection} className="dashboard-section active page-enter">
        <Suspense fallback={<LoadingFallback />}>
          <Component />
        </Suspense>
      </section>
    </div>
  )
}

export default UnifiedDashboard
