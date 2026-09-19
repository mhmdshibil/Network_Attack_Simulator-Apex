# Apex Argus — Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         TRAFFIC SOURCES                                  │
│                                                                          │
│  scripts/generate_*.py        scripts/org_profile.py    sensor_agent.py │
│  (synthetic generators)       (segmented network sim)   (real/demo mode) │
└───────────────────┬───────────────────────┬────────────────────┬─────────┘
                    │ data/raw/*.csv         │ data/raw/          │ POST
                    ▼                        │ org_traffic.csv    │ /api/detections
┌───────────────────────────────────────┐    │                    │
│   auto_attack.py                      │◄───┘                    │
│   Background loop (8–12 s cycle)      │                         │
└───────────────────┬───────────────────┘                         │
                    │ load_all_logs()                              │
                    ▼                                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      log_service.aggregate_by_time_window()              │
│                                                                          │
│  Groups rows by (5-second window, source_ip)                             │
│  Computes 7 features:                                                    │
│    packets_per_second  avg_request_rate  failed_connections  unique_ports │
│    bytes_per_packet    connection_duration    payload_entropy             │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │  feature DataFrame
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      ML DETECTION PIPELINE                               │
│                                                                          │
│  ┌──────────────────────────┐    ┌──────────────────────────────────┐   │
│  │  Random Forest (v2)      │    │  Isolation Forest                │   │
│  │  300 trees, balanced     │    │  Trained on normal traffic only  │   │
│  │  class_weight            │    │  contamination=0.02              │   │
│  │                          │    │                                  │   │
│  │  → 6 attack classes +    │    │  → anomaly score (0–1)          │   │
│  │    confidence (0–1)      │    │  → unknown_anomaly flag         │   │
│  └──────────┬───────────────┘    └──────────────┬───────────────────┘   │
│             │                                    │                        │
│             └──────────────┬─────────────────────┘                        │
│                            │ label + confidence                           │
│                            ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Label resolution:                                                 │  │
│  │    RF=attack              → use RF label + confidence             │  │
│  │    RF=normal + IF=anomaly → "unknown_anomaly" (zero-day path)    │  │
│  │    RF=normal + IF=normal  → skip (benign)                        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬────────────────────────────────────────┘
                                  │ (attack rows only)
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
       ┌────────────────────┐       ┌───────────────────────┐
       │  SHAP Explainer    │       │  MITRE ATT&CK Mapper  │
       │  TreeExplainer     │       │  label → tactic +     │
       │  top-3 features    │       │  technique_id         │
       │  → JSONL store     │       └──────────┬────────────┘
       └──────────┬─────────┘                  │
                  │                             │
                  └──────────────┬──────────────┘
                                 ▼
              ┌──────────────────────────────────────────┐
              │  Response Engine  (response/engine.py)   │
              │                                          │
              │  Threat Intel lookup (AbuseIPDB / VT)    │
              │  threat_score > 80 → escalate to BLOCK   │
              │                                          │
              │  BLOCK / RATE_LIMIT / MONITOR / ALLOW    │
              │  ENFORCE_MODE=dry → log only (safe)      │
              │  ENFORCE_MODE=live → iptables/pfctl      │
              └──────────────────┬───────────────────────┘
                                 │
              ┌──────────────────┼──────────────────────┐
              ▼                  ▼                       ▼
   ┌────────────────┐  ┌──────────────────┐  ┌────────────────────┐
   │  CSV / JSONL   │  │  PostgreSQL /    │  │  WebSocket         │
   │  (primary/     │  │  SQLite (dual-   │  │  broadcast         │
   │   fallback)    │  │  write, guarded) │  │  → React dashboard │
   └────────────────┘  └──────────────────┘  └────────────────────┘
```

**Component descriptions:**

- **Traffic generators** (`scripts/`): Produce synthetic CSV rows for port scan, DDoS, bruteforce, SQL injection, and malware. `org_profile.py` simulates a segmented network with time-of-day volume variation.
- **auto_attack.py**: Background asyncio loop that writes generator output to `data/raw/` every 8–12 seconds, then calls `DetectionEngine.run_once()`.
- **log_service**: Reads all `data/raw/*.csv`, groups by 5-second time window and source IP, and computes 7 engineered features. The bridge between raw event rows and the ML feature space.
- **Detection pipeline**: Two-stage ML classifier (RF + IF) that produces a label, confidence, SHAP explanation, MITRE mapping, and a response decision for every attack window.
- **Response engine**: Stateful policy layer that checks IP reputation, counts prior incidents, and decides BLOCK/RATE_LIMIT/MONITOR/ALLOW. Dry-run safe by default.
- **WebSocket manager**: Singleton that maintains all active client connections and broadcasts detection events in real time.
- **React dashboard**: SPA (no routing library needed) with 11 pages — Dashboard, Live Traffic, Detected Attacks, Analytics, Blocked IPs, Network Map, Triage, Compliance, ML Insights, Roadmap.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React 18 + Vite | SPA dashboard, real-time updates |
| Styling | Plain CSS (Space Grotesk / IBM Plex Mono) | No Tailwind — full control |
| Charts | Recharts | Timeline, analytics, bar charts |
| 3D Background | Three.js | Canvas particle field |
| Backend | FastAPI + Python 3.11 | Async REST API + WebSocket |
| ML | scikit-learn (RF + IF) | Attack classification, anomaly detection |
| Explainability | SHAP (TreeExplainer) | Per-detection feature attributions |
| MITRE | Custom mapping | ATT&CK tactic/technique enrichment |
| Database | PostgreSQL (prod) / SQLite (dev) | Detections, triage, IP reputation |
| Migrations | Alembic | Versioned schema changes |
| Rate limiting | slowapi | 60 req/min per IP |
| Auth | JWT (python-jose) | Optional; off by default |
| Notifications | smtplib + aiohttp | Email + Slack alerts |
| Deployment | Docker Compose + nginx | Single-host container stack |
| CI | GitHub Actions | Build, eval, security scan |
| Security scan | Semgrep + npm audit | Static analysis, dep audit |
| Monitoring (opt) | Wazuh 4.9 | SIEM ingestion of audit JSONL |

---

## ML Pipeline

```
Raw traffic row
  [timestamp, src_ip, dst_ip, dst_port, protocol,
   packet_count, request_rate, success_flag, label,
   bytes_per_packet, connection_duration, payload_entropy]
          │
          ▼ aggregate_by_time_window (5 s, per source IP)
          │
          ▼  7 features
  ┌───────────────────────────────────────────────────────┐
  │  packets_per_second  │ total packets in 5 s window    │
  │  avg_request_rate    │ mean(request_rate)             │
  │  failed_connections  │ count(success_flag == False)   │
  │  unique_ports        │ nunique(destination_port)      │
  │  bytes_per_packet    │ mean(bytes_per_packet)  [v2]   │
  │  connection_duration │ mean(connection_duration) [v2] │
  │  payload_entropy     │ mean(payload_entropy)    [v2]  │
  └───────────────────────────────────────────────────────┘
          │
          ├──────────────────────────────────────┐
          ▼                                      ▼
  Random Forest (300 trees)            Isolation Forest
  class_weight=balanced                contamination=0.02
  min_samples_split=5                  trained on normal only
          │                                      │
          │  label + probas                      │  anomaly score
          ▼                                      ▼
  ┌──────────────────────────────────────────────────────┐
  │              Label Resolution                        │
  │                                                      │
  │  RF ≠ normal              → RF label, RF confidence  │
  │  RF = normal, IF anomalous → "unknown_anomaly"       │
  │  RF = normal, IF normal    → skip                    │
  └──────────────────────────────────────────────────────┘
          │
          ├──────────────────┬───────────────────┐
          ▼                  ▼                   ▼
  SHAP TreeExplainer   MITRE ATT&CK        Response Engine
  top-3 features       mapping             BLOCK / RATE_LIMIT
  stored in JSONL      tactic + technique  / MONITOR / ALLOW
          │                  │                   │
          └──────────────────┴───────────────────┘
                             │
                   detection dict broadcast
                   via WebSocket to dashboard
```

**Why two models?**
The Random Forest excels at classifying *known* attack patterns it was trained on. The Isolation Forest catches *novel* patterns that fall outside the normal traffic distribution — these produce the `unknown_anomaly` label, which represents the zero-day detection path.

**Why payload_entropy?**
This single feature creates near-clean decision boundaries for the two previously hardest classes: SQL injection payloads are structured SQL (low entropy ≈ 2.0–3.5) while malware uses encrypted C2 channels (near-random, entropy ≈ 6.5–8.0). F1 for `sql_injection` improved from 0.86 → 0.969; `malware` from 0.91 → 1.000.

---

## Data Flow

Step-by-step: from packet arrival to WebSocket broadcast.

1. **Generator writes** a batch of CSV rows to `data/raw/<attack_type>.csv` every 8–12 seconds (or via the sensor agent POSTing a feature window directly).
2. **`load_all_logs()`** reads every CSV in `data/raw/`, concatenates them into a single DataFrame.
3. **`aggregate_by_time_window()`** groups rows by `(5s bucket, source_ip)` and computes the 7 features. Old 9-column files (pre-v2) are handled with default fill values for backward compatibility.
4. **`predict()`** runs the feature DataFrame through the Random Forest. `predict_proba()` gives per-class confidence scores.
5. **`is_anomalous()`** runs the same DataFrame through the Isolation Forest. Rows where the RF said "normal" but IF says anomalous become `unknown_anomaly`.
6. **Label resolution** selects the final label and confidence for each source IP group.
7. **`evaluate_and_respond()`** checks IP history, reputation score, and risk threshold to produce a BLOCK/RATE_LIMIT/MONITOR/ALLOW decision.
8. **Threat intel enrichment** (non-blocking): reads cached AbuseIPDB/VirusTotal score; if `threat_score > 80`, escalates action to BLOCK.
9. **SHAP** explains the top-3 feature contributions for the representative row; stored in `data/processed/shap_explanations.jsonl`.
10. **MITRE mapping** looks up tactic + technique_id for the label.
11. **`_log_detection()`** appends a row to `detections.csv` (primary sink). A guarded async task writes the same data to PostgreSQL.
12. **WebSocket broadcast** sends the full detection dict (minus SHAP, which is on-demand) to every connected client. The React dashboard updates in real time.
13. **Notification service** checks severity thresholds in a daemon thread and fires Slack/email if configured.

---

## Storage Architecture

```
data/
├── raw/                         ← Generated CSVs (auto-regenerated; gitignored)
│   ├── normal_traffic.csv       │  12 columns: timestamp…payload_entropy
│   ├── port_scan.csv            │  One file per active attack class
│   └── org_traffic.csv          │  13 columns (+ target_zone for network map)
│
├── processed/                   ← Outputs (gitignored in prod)
│   ├── detections.csv           │  PRIMARY fallback sink — ip, timestamp, label, action, risk_score
│   └── shap_explanations.jsonl  │  {ip, timestamp, label, shap_top3[{feature, shap, rank}]}
│
├── audit/                       ← Audit trail (gitignored in prod)
│   ├── security_events.jsonl    │  Full event log — source for Wazuh SIEM ingestion
│   └── decision_audit.csv       │  Every response engine decision with reason
│
├── policies/                    ← Policy state (persisted across restarts)
│   ├── ip_reputation.json       │  Per-IP: abuse_score, vt_malicious, threat_score, is_known_bad
│   ├── ip_last_seen.json         │  Per-IP: last seen timestamp (for burst detection)
│   ├── hard_blocked_ips.json    │  IPs that have been hard-blocked
│   └── whitelist_ips.json       │  Whitelist overrides
│
└── training/                    ← ML training data (tracked in git)
    └── attack_dataset.csv       │  6000 rows × 8 cols (7 features + label), balanced

models/                          ← Trained models (tracked in git)
├── random_forest.pkl            │  v2: 300 trees, balanced class_weight
├── isolation_forest.pkl         │  Trained on 6628 normal samples
├── random_forest_v1_backup.pkl  │  v1 (4-feature) backup
└── isolation_forest_v1_backup.pkl

PostgreSQL / SQLite tables:
  detections          → ip, timestamp, label, action, risk_score, confidence,
                        target_zone, packets_per_second, avg_request_rate,
                        failed_connections, unique_ports, mitre_tactic, mitre_technique
  triage_cases        → detection_id, ip, label, risk_score, status, notes
  audit_events        → type, ip, timestamp, details (JSON)
  ip_reputation       → ip, abuse_score, vt_malicious, threat_score, is_known_bad, updated_at
```

**Dual-write strategy:** every detection is written to CSV first (synchronously, never fails). The DB write is fire-and-forget in a guarded async task — if the DB is unavailable, CSV continues. The app starts and operates normally without any DB connection.

---

## Deployment Architecture

```
                          Internet / LAN
                                │
                                ▼
                    ┌───────────────────────┐
                    │   Host machine        │
                    │   Port 3000 exposed   │
                    └────────────┬──────────┘
                                 │
                    ┌────────────▼──────────┐
                    │   nginx (container)   │
                    │   Port 80 internal    │
                    │                       │
                    │  • Serves dist/ SPA   │
                    │  • Gzip compression   │
                    │  • Cache headers      │
                    │  • Security headers   │
                    └────────────┬──────────┘
                                 │ (Browser fetches API at :8000)
                                 │
              ┌──────────────────▼──────────────────────┐
              │         Backend (container)              │
              │         Port 8000 exposed                │
              │                                          │
              │  gunicorn + 4 × uvicorn workers          │
              │  FastAPI app                             │
              │  auto_attack_loop (asyncio task)         │
              │  WebSocket manager                       │
              │                                          │
              │  Bind mounts:                            │
              │    ./data   → /app/data                  │
              │    ./models → /app/models                │
              └──────────────────┬──────────────────────┘
                                 │ asyncpg
                    ┌────────────▼──────────┐
                    │  PostgreSQL (container)│
                    │  Port 5432 internal    │
                    │  (not exposed in prod) │
                    │                       │
                    │  Named volume:        │
                    │  postgres_data        │
                    └───────────────────────┘

Optional: Wazuh stack (--profile wazuh)
  wazuh.indexer   port 9200  (internal)
  wazuh.manager   port 55000 (internal + 1514/1515/514)
  wazuh.dashboard port 443   (exposed)
    reads ./data/audit/security_events.jsonl via bind-mount
```

---

## API Reference Summary

```
AUTH
  POST  /api/auth/token          OAuth2 password → JWT
  GET   /api/auth/status         Feature flags: auth_enabled, demo_mode

DETECTION
  GET   /api/detections          Detection log (paginated)
  POST  /api/detections          Ingest feature window (sensor agent)
  POST  /api/detect/run          Manual trigger (admin)
  GET   /api/alerts              Recent alerts

ANALYTICS
  GET   /api/metrics             Aggregate counters
  GET   /api/analytics/timeline  Time-series detections
  GET   /api/analytics/top_attackers
  GET   /api/analytics/attack_trends
  GET   /api/analytics/risk      Risk score over time

SYSTEM
  GET   /api/health              Liveness check
  GET   /api/system/overview     Threat level, active attackers
  GET   /api/system/blocked_ips  Blocked IPs + stats

EXPLAINABILITY
  GET   /api/explain             SHAP explanation for one IP
  GET   /api/explain/summary     Aggregated feature importance (RF Gini + SHAP)

TRIAGE
  GET   /api/triage              Open triage cases
  POST  /api/triage/{id}/resolve Close a case with notes
  GET   /api/triage/stats        Open/closed counts

THREAT INTEL
  GET   /api/threat-intel/{ip}   AbuseIPDB + VirusTotal enrichment
  GET   /api/threat-intel/stats  Cache hit rates, coverage

RESPONSE / AUDIT
  GET   /api/response/decisions  Recent response engine decisions
  GET   /api/audit/events        Security event log
  GET   /api/audit/decisions     Decision audit trail

REPORTS
  GET   /api/reports/weekly      Weekly compliance PDF (ReportLab)

INCIDENTS
  POST  /api/incidents/summarize LLM incident summary (Claude Haiku)

DEMO / SCENARIO
  GET   /api/demo/status         Scheduler state + countdown
  POST  /api/demo/enable         Start auto-attack scheduler (admin)
  POST  /api/demo/disable        Stop scheduler (admin)
  POST  /api/demo/trigger        Fire one attack (analyst)
  POST  /api/scenario/start      Start scripted 5-act scenario (analyst)
  POST  /api/scenario/stop       Stop running scenario (analyst)
  GET   /api/scenario/status     Current act, progress, narrative text

AUTO-ATTACK
  POST  /api/auto-attack/start   Start background attack loop (admin)
  POST  /api/auto-attack/stop    Stop background loop (admin)

NOTIFICATIONS
  GET   /api/notifications/config  Configured channels
  POST  /api/notifications/test    Send test notification (admin)
  GET   /api/notifications/log     Last 50 events

ADMIN
  POST  /api/admin/reset-demo    Clear all detection data (admin, dry mode only)

WEBSOCKET
  WS    /api/ws/detections       Real-time detection + narrative stream
```

---

## Security Model

### Authentication Flow

```
Client                    FastAPI                   JWT
  │                          │                        │
  │  POST /api/auth/token    │                        │
  │  (username, password)    │                        │
  ├─────────────────────────►│                        │
  │                          │  verify credentials    │
  │                          │  bcrypt hash compare   │
  │                          ├───────────────────────►│
  │                          │  sign(payload, secret) │
  │                          │◄───────────────────────┤
  │  {access_token, ...}     │                        │
  │◄─────────────────────────┤                        │
  │                          │                        │
  │  GET /api/detections     │                        │
  │  Authorization: Bearer X │                        │
  ├─────────────────────────►│                        │
  │                          │  require_analyst()     │
  │                          │  decode + verify JWT   │
  │                          ├───────────────────────►│
  │                          │  {sub, role, exp}      │
  │                          │◄───────────────────────┤
  │  200 [detections]        │                        │
  │◄─────────────────────────┤                        │
```

When `AUTH_ENABLED=false` (default), `require_analyst()` and `require_admin()` are no-ops — the API is fully open. This is safe for local demos and single-operator deployments.

### Dry-run vs. Live Enforcement

The response engine always decides (BLOCK/RATE_LIMIT/MONITOR/ALLOW), but the *execution* is gated behind `ENFORCE_MODE`:
- `dry` (default): decisions are logged and broadcast. No OS calls.
- `live`: decisions trigger `iptables -I INPUT -s <ip> -j DROP` (Linux) or `pfctl` (macOS/BSD). Requires an isolated VM and root/sudo.

The `POST /api/admin/reset-demo` endpoint refuses to run when `ENFORCE_MODE=live`, as a safety guard.

### CORS

The CORS policy (`allow_origins=["*"]`) is documented in `SECURITY_SCAN.md` (finding S-01). For a production deployment, narrow this to your frontend's actual origin in `backend/app/main.py`.

### Rate Limiting

slowapi enforces 60 requests/minute per IP address on all routes. The `/api/ws/detections` WebSocket is exempt (it's a long-lived connection, not individual requests).
