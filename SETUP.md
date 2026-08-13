# Setup Guide

Step-by-step instructions for every way to run Apex-Kinetics: Docker (recommended), local development, and model retraining.

---

## Prerequisites

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.11 | 3.14 has a broken `pyexpat` on macOS — use 3.11 or 3.13 |
| Node.js | 18 | Only needed for local frontend dev |
| Docker + Compose | 24 / 2.20 | Required for the Docker path |
| Git | any | — |

---

## Option A — Docker (recommended)

The fastest path. One command starts the backend, frontend, and auto-attack loop.

### 1. Clone and configure

```bash
git clone https://github.com/mhmdshibil/Network_Attack_Simulator-Apex.git
cd Network_Attack_Simulator-Apex

cp .env.example .env
```

Edit `.env` as needed (see [Environment variables](#environment-variables) below). The defaults work out of the box for a local demo.

### 2. Build and start

```bash
docker compose up --build -d
```

Services:
| URL | Service |
|-----|---------|
| `http://localhost:8000` | Backend API |
| `http://localhost:8000/docs` | Interactive API docs (Swagger) |
| `http://localhost:3000` | React dashboard |

The auto-attack loop starts immediately. Open the dashboard and watch detections arrive.

### 3. Stop

```bash
docker compose down
```

Data (detections, audit logs, trained models) is persisted via bind-mounts to `./data/` and `./models/`, so nothing is lost on restart.

---

## Option B — Local development

### 1. Python environment

```bash
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

If `venv` is on Python 3.14 (Homebrew default on macOS), create it explicitly:

```bash
python3.11 -m venv venv --clear
```

### 2. Build the ML models

The pre-trained models are included in `models/`. Skip this step unless you've changed `attack_taxonomy.py` or `dataset_generator.py`.

```bash
# Regenerate training data (6 000 rows, 6 classes with realistic noise)
python -m backend.app.ml.build_dataset

# Train Random Forest (200 estimators, ~30 s)
python -m backend.app.ml.train_model

# Train Isolation Forest anomaly model
python -m backend.app.ml.anomaly_model
```

Run the sanity check to confirm the models work:

```bash
python -m backend.app.ml.sanity_test
# Expected: overall accuracy ~93%, port_scan 100%, sql_injection ~90–95%
```

Run the full evaluation harness:

```bash
python -m backend.app.ml.evaluation_harness
# Expected: RF ~94.7%, baseline ~74.9%, delta +19.8%
```

### 3. Start the backend

```bash
cp .env.example .env            # edit as needed
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The auto-attack loop starts automatically. You'll see `[AUTO] Attack cycle complete` in the logs every 8–12 seconds.

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Vite dev server → http://localhost:5173
```

The frontend proxies API calls to `http://127.0.0.1:8000` by default. To change the backend URL:

```bash
VITE_API_BASE=http://192.168.1.100:8000 npm run dev
```

### 5. Build the frontend (production)

```bash
cd frontend
npm run build
# Output: frontend/dist/  (served by nginx in Docker)
```

---

## Environment variables

Copy `.env.example` to `.env` and set these before starting.

### Authentication

| Variable | Default | Effect |
|----------|---------|--------|
| `AUTH_ENABLED` | `false` | `true` → JWT required on all protected endpoints |
| `JWT_SECRET` | `dev-secret-change-in-production-apex` | Sign JWTs — **set a long random value in production** |
| `ADMIN_PASSWORD` | `adminpass` | Password for the built-in `admin` account |
| `ANALYST_PASSWORD` | `analystpass` | Password for the built-in `analyst` account |

When `AUTH_ENABLED=false` the API is fully open — no login required. The frontend login modal is hidden. Safe for local demos.

When `AUTH_ENABLED=true`:
- `POST /api/auth/token` issues a JWT (OAuth2 password flow)
- Protected endpoints require `Authorization: Bearer <token>`
- The dashboard login modal appears automatically

### Enforcement mode

| Variable | Default | Effect |
|----------|---------|--------|
| `ENFORCE_MODE` | `dry` | `live` → real iptables/pfctl calls (requires root + isolated VM) |

**Leave `ENFORCE_MODE=dry`** unless you are running inside an isolated sandbox VM. In dry-run mode, the response engine logs every decision but never touches the OS firewall.

### LLM summaries

| Variable | Default | Effect |
|----------|---------|--------|
| `ANTHROPIC_API_KEY` | _(empty)_ | Set to enable Claude-powered incident summaries |

Without a key the `/api/incidents/summarize` endpoint returns a graceful fallback message instead of calling the API. All other features work normally.

The model used is `claude-haiku-4-5-20251001`. Each summary is cached in `data/processed/incident_summaries.jsonl` — the API is not called again on repeat requests for the same detection.

### Demo mode

| Variable | Default | Effect |
|----------|---------|--------|
| `DEMO_MODE` | `false` | `true` → demo scheduler starts automatically on boot |
| `DEMO_INTERVAL_SECONDS` | `150` | Seconds between scheduled attacks (clamped 120–300) |

The scheduler can also be toggled at runtime without restarting (see [Demo mode](#demo-mode)).

---

## Demo mode

Designed for live presentations. Each fired attack goes through the real detection pipeline — real RF prediction, real SHAP, real MITRE, real WebSocket push.

### Runtime toggle (no restart needed)

```bash
# Start the scheduler
curl -X POST http://localhost:8000/api/demo/enable

# Stop the scheduler (in-flight attack still completes)
curl -X POST http://localhost:8000/api/demo/disable

# Check status and countdown
curl http://localhost:8000/api/demo/status
```

### Manual trigger

```bash
# Fire a specific attack type immediately (independent of scheduler)
curl -X POST "http://localhost:8000/api/demo/trigger?type=bruteforce"

# Fire a random attack
curl -X POST http://localhost:8000/api/demo/trigger
```

Valid `type` values: `port_scan`, `ddos`, `bruteforce`, `sql_injection`, `malware`.

### Dashboard panel

When demo mode is enabled the **Demo Mode** panel appears in the bottom-right corner of the dashboard. It shows:
- A pill toggle (on/off) wired to the enable/disable endpoints
- A live countdown to the next scheduled attack
- A class dropdown and **Fire** button for on-demand triggers
- The last triggered attack (class, time, detection count)

The toggle requires `admin` role when `AUTH_ENABLED=true`. The Fire button requires `analyst` role.

### Rotation behaviour

The scheduler cycles through all five attack classes in a shuffled order. No class repeats until every class has had a turn. Manual triggers use `random.choice` and do not disturb the rotation.

### Source IPs

Each attack gets a freshly generated globally-routable IPv4 address. The following ranges are always excluded:

```
0.0.0.0/8, 10.0.0.0/8, 100.64.0.0/10 (CGNAT),
127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12,
192.0.0.0/24, 192.168.0.0/16, 198.18.0.0/15,
224.0.0.0/4, 240.0.0.0/4, 255.255.255.255/32
```

---

## Wazuh SIEM integration (optional)

Wazuh is included as an optional `--profile wazuh` service. It forwards `data/audit/security_events.jsonl` as a custom JSON log source with a custom decoder and 7 alert rules.

See [WAZUH_SETUP.md](WAZUH_SETUP.md) for the full walkthrough including certificate generation and dashboard login.

```bash
# One-time: generate TLS certificates
docker compose -f wazuh/generate-indexer-certs.yml run --rm generator

# Start Wazuh alongside the main stack
docker compose --profile wazuh up -d

# Dashboard: https://localhost:443  (admin / SecretPassword)
```

Wazuh requires at least 4 GB of free RAM.

---

## Security scanning

```bash
# Run Semgrep static analysis + npm audit
./scripts/run_security_scan.sh
```

Results are written to `security_scan_reports/`. See [SECURITY_SCAN.md](SECURITY_SCAN.md) for a full report of current findings and their risk assessment.

For Snyk dependency scanning, set `SNYK_TOKEN` before running the script:

```bash
SNYK_TOKEN=your-token ./scripts/run_security_scan.sh
```

---

## Common issues

**Backend won't start — `ModuleNotFoundError`**
Run from the project root (not from `backend/`). The package structure uses `backend.app.*` imports:
```bash
cd /path/to/Network_Attack_Simulator-Apex
uvicorn backend.app.main:app --reload
```

**`pyexpat` import error on macOS**
Python 3.14 from Homebrew has a broken `pyexpat` module. Use 3.11 or 3.13:
```bash
brew install python@3.11
python3.11 -m venv venv
```

**Model file not found**
Pre-trained models are included in `models/`. If they're missing, retrain:
```bash
python -m backend.app.ml.build_dataset
python -m backend.app.ml.train_model
python -m backend.app.ml.anomaly_model
```

**Frontend shows "Backend offline"**
Check that the backend is running on port 8000 and that `VITE_API_BASE` matches. In Docker, the frontend's `VITE_API_BASE` is baked in at build time — rebuild the frontend image if you change the backend address.

**WebSocket not connecting**
The WebSocket endpoint is `ws://localhost:8000/api/ws/detections`. If running behind a reverse proxy, ensure the proxy is configured to upgrade WebSocket connections (`Upgrade: websocket` header). The frontend falls back to polling every 3 seconds if the WebSocket is unavailable.

**Demo panel not showing**
The panel only renders when `demo_mode: true` is returned by `GET /api/auth/status`. Either set `DEMO_MODE=true` in `.env` before starting, or call `POST /api/demo/enable` after startup.
