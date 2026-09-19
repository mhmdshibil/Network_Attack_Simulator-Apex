import React from 'react'
import { Route, Mail } from 'lucide-react'
import './Roadmap.css'

/* Product roadmap — a pitch page for prospective partners. */
const PHASES = [
  {
    id: 1,
    name: 'Intelligence Layer',
    status: 'OPERATIONAL',
    tone: 'operational',
    tagline: 'Current — shipped and running in the live dashboard.',
    sections: [
      {
        heading: 'Built features',
        items: [
          'ML detection pipeline (Random Forest + Isolation Forest)',
          'SHAP explainability per alert',
          'MITRE ATT&CK mapping',
          'LLM-generated incident summaries',
          'Real-time WebSocket SOC dashboard',
          'JWT authentication + role-based access',
          'Full audit trail (CSV + JSONL)',
          'Wazuh SIEM integration',
          'Docker Compose deployment',
        ],
      },
    ],
  },
  {
    id: 2,
    name: 'Real Network Deployment',
    status: 'PILOT READY',
    tone: 'pilot',
    tagline: 'Not yet built — ready to pilot on your existing network infrastructure.',
    timeline: 'Est. 4–6 weeks with pilot partner',
    sections: [
      {
        heading: 'Requirements',
        items: [
          'Network sensor nodes (e.g., Raspberry Pi 4) per monitored subnet',
          'IT department cooperation for SPAN port or subnet access',
          'PostgreSQL for event storage at scale',
        ],
      },
      {
        heading: 'What it adds',
        items: [
          'Live packet capture from real network interfaces',
          'Per-subnet visibility and asset tracking',
          'Baseline calibration to your specific network',
          'Real blocking via iptables on sensor nodes',
        ],
      },
    ],
    cost: 'Infrastructure costs vary by deployment scale. Contact us for a pilot assessment.',
  },
  {
    id: 3,
    name: 'Enterprise Platform',
    status: 'ROADMAP',
    tone: 'roadmap',
    tagline: 'Future vision.',
    timeline: 'Est. Q2 2027',
    sections: [
      {
        heading: 'What it adds',
        items: [
          'Multi-tenant support (multiple sites / organizations)',
          'Compliance reports: ISO 27001, SOC 2, PCI-DSS',
          'Integrations: Splunk, IBM QRadar, Jira, ServiceNow, Slack',
          'Threat intel feeds: AbuseIPDB, VirusTotal, CISA KEV',
          'Mobile push alerts for SOC analysts',
          'Executive SLA dashboard (MTTD, MTTR metrics)',
        ],
      },
    ],
  },
]

function Roadmap() {
  return (
    <div style={{ paddingBottom: '4rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div className="roadmap-eyebrow">
          <Route size={12} style={{ opacity: 0.6 }} /> Product Roadmap
        </div>
        <div className="roadmap-title">Where Apex Argus is going</div>
      </div>

      {/* Vertical timeline */}
      <div className="roadmap-timeline">
        {PHASES.map(phase => (
          <div key={phase.id} className={`roadmap-phase tone-${phase.tone}`}>
            {/* Rail: connecting line + dot */}
            <div className="roadmap-rail">
              <span className={`roadmap-dot dot-${phase.tone}`} />
            </div>

            {/* Card */}
            <div className="roadmap-card">
              <div className="roadmap-card-head">
                <div>
                  <div className="roadmap-phase-kicker">Phase {phase.id}</div>
                  <div className="roadmap-phase-name">{phase.name}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                  <span className={`roadmap-badge badge-${phase.tone}`}>{phase.status}</span>
                  {phase.timeline && (
                    <span style={{
                      fontFamily: "var(--font-mono)", fontSize: '10px',
                      color: 'var(--text-dim)', letterSpacing: '0.04em',
                    }}>
                      {phase.timeline}
                    </span>
                  )}
                </div>
              </div>

              <div className="roadmap-tagline">{phase.tagline}</div>

              {phase.sections.map((sec, i) => (
                <div key={i} className="roadmap-section">
                  <div className="roadmap-section-heading">{sec.heading}</div>
                  <ul className="roadmap-list">
                    {sec.items.map((item, j) => (
                      <li key={j}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}

              {phase.cost && <div className="roadmap-cost">{phase.cost}</div>}
            </div>
          </div>
        ))}
      </div>

      {/* Partner With Us */}
      <div className="roadmap-partner">
        <div className="roadmap-partner-heading">Partner With Us</div>
        <p className="roadmap-partner-text">
          Apex Argus is looking for pilot partners. If you're a network administrator or IT
          manager interested in deploying real-time threat detection on your network,
          we'd like to hear from you.
        </p>
        <a className="roadmap-partner-contact" href="mailto:pilot@apex-argus.io">
          <Mail size={13} /> pilot@apex-argus.io
        </a>
      </div>
    </div>
  )
}

export default Roadmap
