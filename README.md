# Apex Argus — Network Attack Simulator

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

**Python dependencies.** The core stack installs from `requirements.txt`. Two feature dependencies:

```bash
pip install reportlab      # required for the weekly PDF report (GET /api/reports/weekly)
pip install pyshark        # OPTIONAL — only for the sensor agent's SENSOR_MODE=real
```

`pyshark` is not needed for demo mode or normal operation — install it only if you run `sensor_agent.py` with `SENSOR_MODE=real` (which also needs `tshark`/Wireshark and root/CAP_NET_RAW).

---

## Local development

See [SETUP.md](SETUP.md) for the full step-by-step guide including Python environment, model training, and optional integrations.

---

## Database & migrations (Phase 2)

PostgreSQL is the primary store; **CSV/JSONL remain the fallback** — every DB write is fire-and-forget and guarded, so the system works with or without PostgreSQL (and even without the DB packages installed).

- **Local dev (zero setup):** leave `DATABASE_URL` unset or use the SQLite async URL — tables are auto-created on startup:
  ```bash
  export DATABASE_URL=sqlite+aiosqlite:///./apex.db
  ```
- **PostgreSQL (Docker):** `docker compose up` starts a `postgres:16-alpine` service and the backend waits for it (`depends_on … service_healthy`). The backend uses `postgresql+asyncpg://apex:apexpass@postgres:5432/apex`.

**Migrations (Alembic):**
```bash
pip install alembic asyncpg aiosqlite   # if not already installed
export DATABASE_URL=postgresql+asyncpg://apex:apexpass@localhost:5432/apex
alembic upgrade head          # apply the initial schema (detections, audit_events, ip_reputation)
# create a new migration after changing models:
alembic revision --autogenerate -m "describe change"
```

Startup also calls `create_all_tables()` (idempotent) so SQLite/dev works without running Alembic; use Alembic for versioned PostgreSQL schema changes in production.

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

**Threat Intelligence** — every detected IP is cross-referenced against AbuseIPDB, VirusTotal, and a local blocklist (Phase 2). Set `ABUSEIPDB_API_KEY` and/or `VIRUSTOTAL_API_KEY` in `.env` (both free). Results are cached 24h in the `ip_reputation` table; a `threat_score` (AbuseIPDB×0.6 + VirusTotal×0.4) rides along in the detection stream, `threat_score > 80` escalates the action to BLOCK, and the Detected Attacks page shows a clickable **TI Score** badge. Without any key the service falls back to the local CIDR blocklist and the badge shows `TI: OFF`. Endpoints: `GET /api/threat-intel/{ip}` and `GET /api/threat-intel/stats`.

**Notifications** — Apex Argus fires Slack and email alerts when detections cross severity thresholds, with 5-minute IP-level deduplication and per-channel rate limits (10 Slack/min, 20 email/hr). All notification calls are fire-and-forget in daemon threads — they never block the detection pipeline.

*Trigger conditions* (any one is sufficient):
- `attack_type == malware` with confidence > 80%
- `risk_score >= 90` (near-certain high-severity attack)
- `attack_type == ddos` with confidence > 90%
- IP newly added to the block list
- 3+ detections from the same IP within 60 seconds (burst)

*Slack setup* — Create an Incoming Webhook in your Slack workspace (Apps → Incoming Webhooks → Add to Slack), copy the webhook URL, and set `SLACK_WEBHOOK_URL` in `.env`. Messages use Block Kit with attack type, source IP, confidence, action taken, and MITRE technique.

*Email setup (Gmail)* — Enable two-factor authentication on your Google account, go to `myaccount.google.com/apppasswords`, generate an App Password (select "Mail"), and set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASS`, and `ALERT_EMAIL_TO` in `.env`. Any SMTP provider that supports STARTTLS on port 587 works the same way.

Test command (requires admin role or `AUTH_ENABLED=false`):
```bash
curl -X POST http://localhost:8000/api/notifications/test \
  -H "Content-Type: application/json" \
  -d '{"channel":"all"}'
```

| Endpoint | Purpose |
|----------|---------|
| `GET /api/notifications/config` | Check which channels are configured |
| `POST /api/notifications/test` | Send a test notification (admin) |
| `GET /api/notifications/log` | Last 50 notification events (in-memory) |

**Sensor Agent** — `sensor_agent.py` is a standalone bridge between the simulation and a real network. It builds 5-second feature windows (one record per source IP with the four ML features) and POSTs them to the backend. Run it alongside the API:

```bash
# Demo mode (default) — replays the synthetic generators, no privileges needed
python sensor_agent.py

# Real mode — live packet capture (needs pyshark + tshark and root/CAP_NET_RAW)
SENSOR_MODE=real SENSOR_INTERFACE=eth0 sudo -E python sensor_agent.py
```

| Variable | Default | Description |
|----------|---------|-------------|
| `SENSOR_MODE` | `demo` | `demo` replays synthetic generators; `real` captures live packets |
| `SENSOR_INTERFACE` | `eth0` | Network interface to sniff (real mode only) |
| `BACKEND_URL` | `http://localhost:8000` | Backend the agent POSTs windows to |
| `SENSOR_INTERVAL` | `5` | Window length in seconds |

**Demo vs. real.** Demo mode imports the generators in `scripts/`, aggregates a window, and logs `[DEMO] Sending synthetic window: …` — useful for exercising the ingest path with zero setup. Real mode uses `pyshark` to sniff `SENSOR_INTERFACE`, derives `packets_per_second`, `avg_request_rate` (TCP SYN rate), `failed_connections` (TCP RST + ICMP unreachable), and `unique_ports` per source IP, and logs `[REAL] Captured … packets …`. Both modes shut down cleanly on Ctrl+C and never crash on a transient backend outage — they log and retry on the next interval.

> **Production deployment.** Real mode opens a raw capture socket, so it must run with root privileges or the `CAP_NET_RAW` capability (`sudo setcap cap_net_raw+ep $(which python)` for a rootless setup). It also needs `tshark`/Wireshark installed on the host. Deploy one agent per monitored subnet/SPAN port, pointed at a shared `BACKEND_URL`. The agent posts one record per source IP to `POST /api/detections`; each window is scored by the detection engine and, if it's an attack, logged and broadcast over WebSocket (including `target_zone`).

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
