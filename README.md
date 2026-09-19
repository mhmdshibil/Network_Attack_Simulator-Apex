# Apex Argus — Network Security Operations Platform

[![CI](https://github.com/mhmdshibil/Network_Attack_Simulator-Apex/actions/workflows/ci.yml/badge.svg)](https://github.com/mhmdshibil/Network_Attack_Simulator-Apex/actions/workflows/ci.yml)

A full-stack SOC platform that generates synthetic attack traffic, classifies it through a two-stage ML pipeline (Random Forest + Isolation Forest), and surfaces real-time alerts, SHAP explainability, MITRE ATT&CK mappings, and automated triage in a live React dashboard. Built for security education, red-team demos, and academic ML evaluation — not for use against real infrastructure.

---

## ✦ Live Demo

> Deploy in 3 commands — see [Quick Start](#-quick-start) below.  
> Second-screen display board: `http://localhost:3000/demo`

---

## ✦ Key Features

| Detection | Response | Visibility |
|-----------|----------|------------|
| Random Forest (300 trees, 7 features) | Dry-run firewall enforcement | React dashboard, 11 pages |
| Isolation Forest zero-day detection | IP reputation + threat scoring | Live WebSocket feed |
| SHAP feature attribution (top-3) | Slack + email notifications | MITRE ATT&CK enrichment |
| 6 attack classes + unknown_anomaly | Automated triage case creation | Weekly compliance PDF |
| 98.8% accuracy (v2 model) | Audit trail (CSV + JSONL) | ML Insights page (SHAP + Gini) |
| Sensor agent (real + demo mode) | JWT auth, rate limiting | Scenario player (5-act demo) |

---

## ✦ Architecture

```
Generators / sensor_agent.py
        │
        ▼
log_service — 5 s windows × 7 features
        │
        ├──► Random Forest ──► label + confidence
        │                             │
        └──► Isolation Forest ──► anomaly score
                                      │
                              Label resolution
                         (unknown_anomaly for zero-days)
                                      │
              ┌───────────────────────┼────────────────────┐
              ▼                       ▼                    ▼
        SHAP top-3           MITRE ATT&CK         Response engine
        (stored JSONL)        mapping             BLOCK / RATE_LIMIT
                                                  / MONITOR / ALLOW
                                      │
                          WebSocket broadcast
                                      │
                          React dashboard (live)
```

Full diagram with all components → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## ✦ ML Performance

v2 model — 7 features, 300 trees, `class_weight="balanced"`

| Class | Precision | Recall | F1 |
|-------|-----------|--------|----|
| bruteforce | 1.000 | 0.987 | 0.993 |
| ddos | 1.000 | 1.000 | 1.000 |
| malware | 1.000 | 1.000 | 1.000 |
| normal | 0.943 | 0.987 | 0.964 |
| port_scan | 1.000 | 1.000 | 1.000 |
| sql_injection | 0.986 | 0.953 | 0.969 |
| **overall** | | | **0.988** |

Naive threshold baseline: 0.767 · **Δ +22.1 pp**  
`sql_injection` F1 improved 0.86 → 0.969 with the `payload_entropy` feature.  
→ Full evaluation: [docs/EVALUATION_REPORT.md](docs/EVALUATION_REPORT.md)

---

## ✦ Quick Start

```bash
git clone https://github.com/mhmdshibil/Network_Attack_Simulator-Apex.git
cd Network_Attack_Simulator-Apex

cp .env.example .env          # defaults work out of the box

docker compose up --build -d
```

| URL | Service |
|-----|---------|
| `http://localhost:3000` | React dashboard |
| `http://localhost:8000/docs` | Interactive API docs (Swagger) |
| `http://localhost:3000/demo` | Second-screen display board |

The auto-attack loop starts immediately. Detections appear within 10 seconds.

**Local dev** (no Docker) → [SETUP.md](SETUP.md)  
**Production** → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ✦ Demo Mode

Fires one scripted attack every N seconds through the real detection pipeline.

```bash
# Toggle at runtime — no restart needed
curl -X POST http://localhost:8000/api/demo/enable
curl -X POST http://localhost:8000/api/demo/trigger?type=malware
```

**Keyboard shortcuts** (active when Demo Panel is open):

| Key | Action |
|-----|--------|
| `D` | Fire one random attack |
| `S` | Start Corporate Breach scenario |
| `X` | Stop scenario |
| `R` | Reset demo data |
| `?` | Toggle shortcuts help |

**Scenario player** — 5-act "Corporate Breach Attempt": Recon → Credential Access → Exploitation → Lateral Movement → DDoS. Scripted detections with a live narrative overlay on the dashboard.

---

## ✦ Configuration

**Core**

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_ENABLED` | `false` | Enforce JWT on all endpoints |
| `JWT_SECRET` | dev key | Sign JWTs — generate with `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | `adminpass` | Built-in admin account |
| `ANALYST_PASSWORD` | `analystpass` | Built-in analyst account |
| `ENFORCE_MODE` | `dry` | `live` triggers real iptables (isolated VM only) |
| `ORG_NAME` | `Your Organization` | Printed on compliance PDF |
| `TRAFFIC_PROFILE` | `org` | `org` = segmented network; `default` = simple mix |

**Optional integrations**

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | LLM incident summaries (Claude Haiku) |
| `ABUSEIPDB_API_KEY` | Threat intelligence scoring |
| `VIRUSTOTAL_API_KEY` | Threat intelligence scoring |
| `SLACK_WEBHOOK_URL` | Slack alert notifications |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` | Email notifications |
| `DATABASE_URL` | PostgreSQL (default) or `sqlite+aiosqlite:///./apex.db` |

Full variable reference → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ✦ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, plain CSS |
| Charts | Recharts, Three.js (particle background) |
| Backend | FastAPI, Python 3.11, asyncio |
| ML | scikit-learn (RF + IF), SHAP |
| Database | PostgreSQL + Alembic (SQLite for dev) |
| Auth | JWT (python-jose), slowapi rate limiting |
| Deploy | Docker Compose, nginx, gunicorn + uvicorn |
| CI | GitHub Actions |
| SIEM (opt) | Wazuh 4.9 |

---

## ✦ Project Structure

```
.
├── backend/app/
│   ├── api/          # FastAPI routers (one file per feature area)
│   ├── ml/           # RF, IF, SHAP, evaluation harness, dataset builder
│   ├── response/     # Decision engine + dry-run enforcement
│   └── services/     # Detection, auto-attack, demo, WebSocket, notifications
├── frontend/src/
│   ├── api/          # api.js — all fetch wrappers
│   ├── components/   # Sidebar, DemoPanel, NarrativeOverlay, LoginModal
│   ├── hooks/        # useDetectionStream, useCountUp, useDemoShortcuts
│   └── pages/        # 11 dashboard pages + DemoLanding
├── scripts/          # Traffic generators (6 attack types + org profile)
├── docs/             # ARCHITECTURE.md, EVALUATION_REPORT.md, DEPLOYMENT.md
├── models/           # Trained .pkl files (tracked in git)
├── data/training/    # attack_dataset.csv (tracked in git)
├── docker-compose.yml          # Development stack
├── docker-compose.prod.yml     # Production stack
└── sensor_agent.py             # Standalone real/demo network sensor
```

---

## ✦ Deployment

```bash
# Production (gunicorn + resource limits)
docker compose -f docker-compose.prod.yml up -d --build
```

→ Step-by-step guide: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## ✦ Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| 1–2 | RF classifier, synthetic generators, PostgreSQL | ✅ done |
| 3 | Isolation Forest, MITRE, hard-block policy, audit trail | ✅ done |
| 4 | SHAP explainability, LLM summaries, JWT auth | ✅ done |
| 5 | Threat Intel (AbuseIPDB + VirusTotal), triage, notifications | ✅ done |
| 6 | Network Map, sensor agent, org traffic profile | ✅ done |
| 7 | Alert triage, compliance PDF, Wazuh SIEM integration | ✅ done |
| 4A | Demo polish: scenario player, keyboard shortcuts, /demo page | ✅ done |
| 4B | 7-feature v2 model, 98.8% accuracy, ML Insights page | ✅ done |
| 4C | Production Docker, CI pipeline, architecture docs | ✅ done |
| — | Streaming ingest (Kafka/Redpanda), multi-tenant, RBAC | planned |

---

## ✦ Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — adding attack types, API endpoints, and frontend pages all follow documented patterns.

---

## ✦ License

MIT
