# Apex Argus — Deployment Guide

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Docker | 24.0 | `docker --version` |
| Docker Compose | v2.20 | `docker compose version` (note: no hyphen) |
| RAM | 2 GB free | 4 GB recommended with Wazuh enabled |
| Disk | 2 GB free | Models + PostgreSQL volume |
| Ports available | 3000, 8000 | 5432 is internal in prod compose |

---

## Quick Deploy (Docker)

```bash
# 1. Clone the repository
git clone https://github.com/mhmdshibil/Network_Attack_Simulator-Apex.git
cd Network_Attack_Simulator-Apex

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — at minimum set ORG_NAME. Defaults work for local demo.

# 3. Build and start all services
docker compose up --build -d
```

**What each command does:**
- `git clone` — downloads ~50 MB including pre-trained models and training data
- `cp .env.example .env` — creates your local config (never committed to git)
- `docker compose up --build -d` — builds two images (backend ~800 MB, frontend ~50 MB), starts PostgreSQL, backend (uvicorn), and nginx frontend in detached mode

Services are healthy within ~60 seconds. The auto-attack loop begins immediately.

```bash
# Stop all services (data is preserved in ./data/ and ./models/)
docker compose down

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

---

## Environment Configuration

Copy `.env.example` to `.env` and configure before starting.

### Core

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ORG_NAME` | `Your Organization` | Yes | Printed on compliance PDF reports |
| `TRAFFIC_PROFILE` | `org` | No | `org` = segmented network; `default` = simple mix |
| `ENFORCE_MODE` | `dry` | No | `dry` = log only; `live` = real iptables (isolated VM) |

### Auth

| Variable | Default | Notes |
|----------|---------|-------|
| `AUTH_ENABLED` | `false` | Set `true` for any shared deployment |
| `JWT_SECRET` | dev fallback | **Must change for production** — `openssl rand -hex 32` |
| `ADMIN_PASSWORD` | `adminpass` | Change before any shared use |
| `ANALYST_PASSWORD` | `analystpass` | Change before any shared use |

### Database

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://apex:apexpass@postgres:5432/apex` | PostgreSQL via Docker |
| — | `sqlite+aiosqlite:///./apex.db` | Local dev without Docker |

### Notifications (all optional)

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Incoming Webhook URL — Slack → Apps → Incoming Webhooks |
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` (STARTTLS) |
| `SMTP_USER` | Sender email address |
| `SMTP_PASS` | App password (Gmail: `myaccount.google.com/apppasswords`) |
| `ALERT_EMAIL_TO` | Recipient address |

### Sensor

| Variable | Default | Description |
|----------|---------|-------------|
| `SENSOR_MODE` | `demo` | `demo` = synthetic; `real` = live capture |
| `SENSOR_INTERFACE` | `eth0` | Interface to sniff (real mode only) |
| `BACKEND_URL` | `http://localhost:8000` | Where the agent POSTs windows |
| `SENSOR_INTERVAL` | `5` | Window length in seconds |

### Demo

| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO_MODE` | `false` | Auto-start demo scheduler on boot |
| `DEMO_INTERVAL_SECONDS` | `150` | Seconds between auto-attacks (120–300) |

### Threat Intelligence (both free tier)

| Variable | Description |
|----------|-------------|
| `ABUSEIPDB_API_KEY` | 1000 req/day — [abuseipdb.com](https://abuseipdb.com) |
| `VIRUSTOTAL_API_KEY` | 500 req/day — [virustotal.com](https://virustotal.com) |

### LLM

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude Haiku incident summaries — degrades gracefully if absent |

### Frontend Build

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE` | `http://localhost:8000` | Backend URL baked into frontend at build time |

---

## First Run Checklist

1. **Copy env file**
   ```bash
   cp .env.example .env
   ```

2. **Set JWT secret** (required for `AUTH_ENABLED=true`)
   ```bash
   openssl rand -hex 32
   # Paste output into .env as JWT_SECRET=<value>
   ```

3. **Set organisation name**
   ```
   ORG_NAME=Acme Security Lab
   ```

4. **Start the stack**
   ```bash
   docker compose up --build -d
   ```

5. **Verify backend is healthy**
   ```bash
   curl http://localhost:8000/api/health
   # Expected: {"status":"ok"}
   ```

6. **Open dashboard**
   ```
   http://localhost:3000
   ```
   Detections will start appearing within ~10 seconds.

7. *(Optional)* **Add threat intelligence API keys** in `.env`, then `docker compose restart backend`

8. *(Optional)* **Enable Slack/email notifications** in `.env`, then:
   ```bash
   curl -X POST http://localhost:8000/api/notifications/test \
     -H "Content-Type: application/json" \
     -d '{"channel":"all"}'
   ```

9. *(Optional)* **Enable auth** — set `AUTH_ENABLED=true`, `JWT_SECRET`, strong passwords. Restart backend.

---

## Production Deployment

Use `docker-compose.prod.yml` for hardened production settings:

```bash
cp .env.production.example .env
# Edit .env — set JWT_SECRET, passwords, VITE_API_BASE to your server IP

docker compose -f docker-compose.prod.yml up -d --build
```

**What's different in prod mode:**
- Backend runs gunicorn with 4 uvicorn workers (no `--reload`)
- Resource limits: backend 512 MB / 0.5 CPU, frontend 128 MB / 0.25 CPU, postgres 256 MB / 0.25 CPU
- PostgreSQL port is **not** exposed to the host (internal only)
- All services restart `unless-stopped`

**To update** (pull latest + rebuild):
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
# Zero-downtime: Compose rebuilds one container at a time
```

**Run database migrations after updates:**
```bash
docker compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head
```

---

## Sensor Deployment (Real Network)

Deploy `sensor_agent.py` on any host that has network visibility (e.g. a SPAN port, a gateway, or a monitoring VLAN).

1. **Install dependencies on the sensor host**
   ```bash
   pip install requests pyshark
   # Also install tshark/Wireshark: apt install tshark or brew install wireshark
   ```

2. **Configure environment**
   ```bash
   export SENSOR_MODE=real
   export SENSOR_INTERFACE=eth0        # check: ip link show
   export BACKEND_URL=http://192.168.1.50:8000   # your Apex Argus instance
   export SENSOR_INTERVAL=5
   ```

3. **Run with capture capability**
   ```bash
   sudo -E python sensor_agent.py
   # Or rootless (grant capability once):
   sudo setcap cap_net_raw+ep $(which python3)
   python sensor_agent.py
   ```

4. **Verify capture before going live**
   ```bash
   SENSOR_MODE=real python sensor_agent.py --test-capture
   # Captures 10 seconds and prints a per-IP summary table (no posting)
   ```

5. **Point at your Apex Argus instance** — set `BACKEND_URL` to the host running the backend API. The sensor POSTs one feature record per source IP to `POST /api/detections`.

Deploy one agent per monitored subnet or SPAN port for multi-zone coverage.

---

## Backup and Recovery

**What to back up:**

| Path | Contents | Frequency |
|------|----------|-----------|
| `.env` | All secrets and config | Once + on change |
| `data/` | Detections, audit logs, policies | Daily |
| `models/` | Trained ML models | After retraining |

**Simple backup:**
```bash
tar czf apex-backup-$(date +%Y%m%d).tar.gz data/ models/ .env
```

**PostgreSQL backup (prod):**
```bash
docker compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U apex apex > apex-db-$(date +%Y%m%d).sql
```

**Restore:**
```bash
# Restore files
tar xzf apex-backup-20260101.tar.gz

# Restore PostgreSQL
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U apex apex < apex-db-20260101.sql
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ModuleNotFoundError` on backend start | Running from wrong directory | Run from project root: `cd /path/to/Apex && uvicorn backend.app.main:app` |
| `pyexpat` import error (macOS) | Python 3.14 Homebrew bug | Use Python 3.11: `brew install python@3.11` |
| Model file not found | models/ not mounted / deleted | `docker compose down && docker compose up --build` — models are in the image |
| Frontend shows "Backend offline" | `VITE_API_BASE` mismatch | Set correct URL in `.env`, rebuild frontend: `docker compose up --build frontend` |
| WebSocket not connecting | Proxy not upgrading WS | Configure proxy: `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"` |
| Demo panel not showing | `demo_mode` flag is false | `curl -X POST http://localhost:8000/api/demo/enable` |
| DB write failed (non-fatal) | PostgreSQL not yet healthy | Wait 30 s — backend retries; CSV sink keeps working regardless |
| Port 5432 already in use | Local PostgreSQL running | Stop local PG or change compose port: `"5433:5432"` in `docker-compose.yml` |
| `gunicorn: command not found` | Old backend image cached | `docker compose -f docker-compose.prod.yml build --no-cache backend` |
| Wazuh dashboard unreachable | TLS certs not generated | Run cert generator first: `docker compose -f wazuh/generate-indexer-certs.yml run --rm generator` |
