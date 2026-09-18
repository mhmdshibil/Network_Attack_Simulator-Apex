import React from 'react'
import Dashboard from './Dashboard'
import LiveTraffic from './LiveTraffic'
import DetectedAttacks from './DetectedAttacks'
import RiskAnalysis from './RiskAnalysis'
import AttackAnalytics from './AttackAnalytics'
import BlockedIPs from './BlockedIPs'
import NetworkMap from './NetworkMap'
import Triage from './Triage'
import Compliance from './Compliance'
import Roadmap from './Roadmap'

const sections = {
  dashboard:         { component: Dashboard },
  'live-traffic':    { component: LiveTraffic },
  'detected-attacks':{ component: DetectedAttacks },
  'risk-analysis':   { component: RiskAnalysis },
  'attack-analytics':{ component: AttackAnalytics },
  'blocked-ips':     { component: BlockedIPs },
  'network-map':     { component: NetworkMap },
  'triage':          { component: Triage },
  'compliance':      { component: Compliance },
  'roadmap':         { component: Roadmap },
}

function UnifiedDashboard({ activeSection }) {
  return (
    <div className="unified-dashboard">
      {Object.entries(sections).map(([key, { component: Component }]) => (
        <section
          key={key}
          className={`dashboard-section ${activeSection === key ? 'active' : 'inactive'}`}
        >
          <Component />
        </section>
      ))}
    </div>
  )
}

export default UnifiedDashboard
