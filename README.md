# Apex-Kinetics — Network Attack Simulator

A full-stack SOC (Security Operations Center) simulation platform. Generates synthetic network attack traffic, runs it through a real ML detection pipeline, and surfaces alerts, SHAP explanations, MITRE ATT&CK mappings, and LLM-generated incident summaries in a live dashboard.

Built for security education, red-team demos, and ML-model experimentation — not for use against real infrastructure.

---

## Architecture at a glance

```
Synthetic traffic generators  ──►  data/raw/*.csv
                                        │
                               log_service (aggregate 5 s windows)
                                        │
                          Random Forest + Isolation Forest
                                        │
                     ┌──────────────────┼──────────────────┐
                     │                  │                  │
               SHAP top-3        MITRE ATT&CK         Response engine
               explanation        mapping              (dry-run block /
               stored to          enrichment           rate-limit / log)
               JSONL                                        │
                     │                  │                  │
                     └──────────────────┴──────────────────┘
                                        │
                               WebSocket broadcast
                                        │
                              React dashboard (live)
```

The backend is FastAPI + Python. The frontend is React + Vite, plain CSS with a monochrome design system. No Tailwind.

---

## Feature overview

| Phase | Feature |
|-------|---------|
| 1 | Random Forest classifier on 4 engineered traffic features |
| 2 | Synthetic attack generators: port scan, DDoS, bruteforce, SQL injection, malware |
| 3 | Isolation Forest anomaly layer → `unknown_anomaly` zero-day label |
| 4 | Dry-run response engine (firewall block / rate-limit / log) gated behind `ENFORCE_MODE=live` |
| 5 | MITRE ATT&CK enrichment for all 6 attack labels |
| 6 | Hard-block policy with IP reputation tracking |
| 7 | Evaluation harness: RF vs. naive threshold baseline, F1 per class, FPR |
| 8 | Autonomous response with full audit trail |
| 9 | Decision audit CSV + security events JSONL |
| 10 | LLM incident summaries via Claude (optional, degrades gracefully) |
| 11 | JWT auth (`AUTH_ENABLED`), rate limiting (60 req/min via slowapi) |
| 12 | Docker Compose: backend + nginx-fronted React frontend |
| 13 | Semgrep static analysis + npm audit security scan |
| 14 | Wazuh single-node SIEM stack (optional `--profile wazuh`) |
| 15 | Monochrome SOC UI: Space Grotesk / IBM Plex Mono, Canvas 2D particle background wired to live WebSocket detections |
| 16 | Demo / showcase mode: runtime toggle, shuffled rotation, manual trigger |

---

## Quick start (Docker)

```bash
git clone https://github.com/mhmdshibil/Network_Attack_Simulator-Apex.git
cd Network_Attack_Simulator-Apex

cp .env.example .env          # edit if needed
docker compose up --build -d

# Backend API  →  http://localhost:8000
# Dashboard    →  http://localhost:3000
# API docs     →  http://localhost:8000/docs
```

Everything is running. The auto-attack loop starts immediately and generates detections every 8–12 seconds. Open the dashboard to watch alerts arrive in real time.

---

## Local development

See [SETUP.md](SETUP.md) for the full step-by-step guide including Python environment, model training, and optional integrations.

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_ENABLED` | `false` | Enforce JWT on all protected endpoints |
| `JWT_SECRET` | dev fallback | Secret for signing tokens — **change in production** |
| `ADMIN_PASSWORD` | `adminpass` | Password for the `admin` user |
| `ANALYST_PASSWORD` | `analystpass` | Password for the `analyst` user |
| `ENFORCE_MODE` | `dry` | `live` activates real iptables/pfctl — requires isolated VM |
| `ANTHROPIC_API_KEY` | _(empty)_ | Enables LLM incident summaries via Claude Haiku |
| `DEMO_MODE` | `false` | Start demo scheduler automatically on boot |
| `DEMO_INTERVAL_SECONDS` | `150` | Seconds between scheduled demo attacks (120–300) |
| `VITE_API_BASE` | `http://127.0.0.1:8000` | Backend URL baked into the frontend bundle |

---

## Demo / showcase mode

Designed for live presentations. Fires one attack every N seconds in a shuffled rotation across all five attack classes, with a fresh globally-routable source IP each time.

**Runtime toggle (no restart needed):**

```bash
# Start scheduler
curl -X POST http://localhost:8000/api/demo/enable

# Stop scheduler
curl -X POST http://localhost:8000/api/demo/disable

# Fire one attack immediately (independent of scheduler state)
curl -X POST "http://localhost:8000/api/demo/trigger?type=ddos"

# Status + countdown
curl http://localhost:8000/api/demo/status
```

The **Demo Mode** panel appears in the bottom-right of the dashboard when `DEMO_MODE=true` or after calling `/enable`. It has a pill toggle, class dropdown, Fire button, and a live countdown.

---

## API reference

Full interactive docs at `http://localhost:8000/docs`. Key endpoint groups:

| Prefix | Purpose |
|--------|---------|
| `GET /api/health` | Liveness check |
| `GET /api/detections` | Detection log (paginated) |
| `GET /api/alerts` | Recent alerts |
| `GET /api/analytics/*` | Timeline, top attackers, attack trends, risk |
| `GET /api/metrics` | Aggregate counters |
| `GET /api/system/overview` | Threat level, active attackers |
| `GET /api/system/blocked_ips` | Blocked IP list + stats |
| `POST /api/auto-attack/start|stop` | Toggle background attack loop |
| `POST /api/demo/enable|disable` | Toggle demo scheduler (admin) |
| `POST /api/demo/trigger` | Fire one attack on demand (analyst) |
| `GET /api/demo/status` | Scheduler state + countdown (analyst) |
| `POST /api/incidents/summarize` | Generate LLM incident summary |
| `GET /api/explain` | SHAP explanation for a detection |
| `POST /api/auth/token` | Get JWT (OAuth2 password flow) |
| `GET /api/auth/status` | Feature flags: auth_enabled, demo_mode |
| `WS /api/ws/detections` | Real-time detection stream |

---

## ML pipeline

**Features** (aggregated per 5-second window per source IP):
- `packets_per_second` — total packets in window
- `avg_request_rate` — mean request rate
- `failed_connections` — count of failed TCP handshakes / auth failures
- `unique_ports` — distinct destination ports contacted

**Models:**
- **Random Forest** (200 estimators) — classifies into 5 attack types + normal
- **Isolation Forest** — flags anomalous traffic that RF classifies as normal → `unknown_anomaly`

**Evaluation** (run `python -m backend.app.ml.evaluation_harness`):
- RF overall accuracy: ~94.7% vs. 74.9% naive threshold baseline (+19.8%)
- Hardest class: `sql_injection` (F1 ≈ 0.86) due to overlap with normal browsing traffic
- Easiest class: `port_scan` (F1 = 1.00) — unique_ports is a near-perfect signal

To retrain after changing `attack_taxonomy.py`:
```bash
python -m backend.app.ml.build_dataset
python -m backend.app.ml.train_model
python -m backend.app.ml.anomaly_model
```

---

## Security notes

- `ENFORCE_MODE=dry` (default) — the response engine logs decisions but never touches iptables or pfctl. Set `ENFORCE_MODE=live` only inside an isolated sandbox VM.
- `AUTH_ENABLED=false` (default) — the API is open. Enable auth for any shared deployment.
- The CORS wildcard (`allow_origins=["*"]`) is flagged in `SECURITY_SCAN.md`. Browsers reject wildcard + credentials per spec, making it safe for the local demo use case, but narrow it for production.
- See `SECURITY_SCAN.md` for the full Semgrep + npm audit report.

---

## Optional integrations

**Wazuh SIEM** — see [WAZUH_SETUP.md](WAZUH_SETUP.md)

```bash
# Generate TLS certs first (one-time)
docker compose -f wazuh/generate-indexer-certs.yml run --rm generator

# Start Wazuh alongside the main stack
docker compose --profile wazuh up -d
# Dashboard: https://localhost:443  (admin / SecretPassword)
```

**LLM summaries** — set `ANTHROPIC_API_KEY` in `.env`. Uses `claude-haiku-4-5` with a structured SOC-analyst prompt. Results are cached in `data/processed/incident_summaries.jsonl`.

---

## Project layout

```
.
├── backend/
│   └── app/
│       ├── api/            # FastAPI routers (one file per feature area)
│       ├── audit/          # Event building + JSONL/CSV writers
│       ├── core/           # Paths, auth, config
│       ├── ml/             # Model training, SHAP, evaluation harness
│       ├── response/       # Decision engine + dry-run enforcement
│       └── services/       # Detection, auto-attack, demo, LLM, WebSocket
├── data/
│   ├── audit/              # decision_audit.csv, security_events.jsonl
│   ├── policies/           # ip_reputation.json, hard_blocked_ips.json
│   ├── processed/          # detections.csv, shap_explanations.jsonl
│   ├── raw/                # Live synthetic traffic CSVs (auto-generated)
│   └── training/           # attack_dataset.csv (built by build_dataset.py)
├── frontend/
│   └── src/
│       ├── api/            # api.js — all fetch wrappers
│       ├── components/     # Sidebar, ParticleBackground, DemoPanel, LoginModal
│       ├── context/        # AuthContext
│       ├── hooks/          # useDetectionStream, useCountUp
│       └── pages/          # Dashboard, LiveTraffic, DetectedAttacks, ...
├── models/                 # random_forest.pkl, isolation_forest.pkl
├── scripts/                # Traffic generators + security scan runner
├── wazuh/                  # Wazuh config, decoders, rules
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
├── SETUP.md
├── SECURITY_SCAN.md
└── WAZUH_SETUP.md
```

---

## License

MIT
