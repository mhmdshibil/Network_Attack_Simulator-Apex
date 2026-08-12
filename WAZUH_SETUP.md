# Wazuh Integration Setup — Phase 14

Wazuh adds host-level behavioural monitoring and a full SIEM dashboard on top of the existing NAS pipeline. Our security_events.jsonl is forwarded into Wazuh as a custom log source, so its dashboard shows NAS detections alongside Wazuh's own host-level alerts.

The Wazuh stack runs under the `wazuh` Docker Compose profile and does **not** start with `docker compose up -d` by default — the existing backend + frontend stack is unaffected.

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Docker Engine | 20.10+ |
| Docker Compose | 2.x (v2 plugin) |
| Free RAM | **≥ 4 GB** for the Wazuh stack (indexer + manager + dashboard) |
| Free disk | ~5 GB (indexer data + images) |
| Ports free on host | 443, 1514, 1515, 9200, 55000 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Docker host                                            │
│                                                         │
│  ┌──────────┐  ┌──────────┐    ┌─────────────────────┐ │
│  │ backend  │  │ frontend │    │  (wazuh profile)    │ │
│  │ :8000    │  │ :3000    │    │  ┌───────────────┐  │ │
│  └──────────┘  └──────────┘    │  │ wazuh.manager │  │ │
│                                │  │  :1514 :55000 │  │ │
│  data/audit/                   │  └───────┬───────┘  │ │
│  security_events.jsonl ────────┼──── bind │mount     │ │
│  (read-only)                   │  ┌───────▼───────┐  │ │
│                                │  │ wazuh.indexer │  │ │
│                                │  │  :9200        │  │ │
│                                │  └───────────────┘  │ │
│                                │  ┌───────────────┐  │ │
│                                │  │wazuh.dashboard│  │ │
│                                │  │  :443         │  │ │
│                                │  └───────────────┘  │ │
│                                └─────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Step-by-step setup

### Step 1 — Generate SSL certificates (one time only)

The Wazuh indexer and dashboard communicate over mutual TLS. You must generate certificates before starting the stack for the first time.

```bash
# From the project root:
docker compose -f wazuh/generate-indexer-certs.yml run --rm generator
```

This creates the following files under `wazuh/config/wazuh_indexer_ssl_certs/`:
```
admin-key.pem
admin.pem
root-ca-manager.pem
root-ca.pem
wazuh.dashboard-key.pem
wazuh.dashboard.pem
wazuh.indexer-key.pem
wazuh.indexer.pem
wazuh.manager-key.pem
wazuh.manager.pem
```

These are gitignored — regenerate them on each new deployment. Do **not** commit them.

Add this to `.gitignore` if not already there:
```
wazuh/config/wazuh_indexer_ssl_certs/
```

### Step 2 — (Optional) Set custom passwords via .env

The defaults work for a local demo. For any non-local deployment, override them:

```bash
# In your .env (already gitignored via .env.example pattern):
WAZUH_INDEXER_PASSWORD=YourStrongPasswordHere
WAZUH_API_PASSWORD=YourWazuhApiPassword*1
WAZUH_DASHBOARD_PASSWORD=YourDashboardPassword
```

### Step 3 — Start the Wazuh stack

```bash
docker compose --profile wazuh up -d
```

This starts `wazuh.indexer`, `wazuh.manager`, and `wazuh.dashboard` without touching the running `backend` and `frontend` containers.

First startup takes **3–5 minutes** — the indexer runs security configuration and the manager initialises its rule engine. Monitor progress with:

```bash
docker compose logs -f wazuh.manager wazuh.indexer
```

You're ready when you see: `INFO: Starting wazuh-manager` in the manager logs and the indexer health check turns green.

### Step 4 — Access the Wazuh dashboard

Open: **https://localhost** (port 443)

Accept the self-signed certificate warning (expected for a local deployment).

| Credential | Value |
|-----------|-------|
| Username | `admin` |
| Password | `SecretPassword` (or your `WAZUH_INDEXER_PASSWORD`) |

> The dashboard may take an additional minute after the containers start to become responsive.

### Step 5 — Verify the NAS log source is active

In the Wazuh dashboard:

1. Go to **Server Management → Settings → Ruleset → Decoders**
2. Search for `nas-detection` — you should see the custom decoder imported from `wazuh/decoders/custom_nas.xml`
3. Go to **Server Management → Settings → Ruleset → Rules**
4. Search for `100001` — the base NAS rule should appear
5. Go to **Dashboards → Security events** and filter by rule group `nas` — any existing entries in `data/audit/security_events.jsonl` will appear here within 30–60 seconds of the manager starting

If no events appear:
```bash
# Check if the file is mounted and has content
docker compose exec wazuh.manager ls -lh /var/log/nas/
docker compose exec wazuh.manager head -1 /var/log/nas/security_events.jsonl

# Check manager logs for decoder errors
docker compose exec wazuh.manager tail -50 /var/ossec/logs/ossec.log
```

---

## What gets forwarded into Wazuh

The bind mount in docker-compose.yml:
```yaml
- ./data/audit/security_events.jsonl:/var/log/nas/security_events.jsonl:ro
```

...combined with the `<localfile>` block in `wazuh/config/wazuh_cluster/wazuh_manager.conf`:
```xml
<localfile>
  <log_format>json</log_format>
  <location>/var/log/nas/security_events.jsonl</location>
  <label key="source">nas-detection</label>
</localfile>
```

Wazuh reads the JSONL file as a JSON log. New lines appended by the NAS backend are detected within ~1 second (Wazuh uses `inotify`-style monitoring). Each event is parsed by the `nas-detection-json` decoder and matched against the custom rules (`100001`–`100007`).

### Custom rules overview

| Rule ID | Trigger | Level | MITRE |
|---------|---------|-------|-------|
| 100001 | Any NAS event | 3 | — |
| 100002 | HARD_BLOCK / SOFT_BLOCK / RATE_LIMIT decision | 7 | T1046 |
| 100003 | HARD_BLOCK specifically | 10 | — |
| 100004 | `attack_type: bruteforce` | 8 | T1110 |
| 100005 | `attack_type: ddos` | 9 | T1498 |
| 100006 | `attack_type: unknown_anomaly` | 6 | T1036 |
| 100007 | `attack_type: sql_injection` | 8 | T1190 |

Wazuh level 10 = critical; level 3 = informational. Hard-block events will appear in the Wazuh security events with a red critical badge.

---

## Stopping Wazuh (without affecting the main stack)

```bash
docker compose --profile wazuh down
# Wazuh data volumes are preserved; restart picks up where it left off.

# To also wipe Wazuh state:
docker compose --profile wazuh down -v
```

---

## Known limitations and blockers

### 1. Certificate generation is a manual prerequisite
Wazuh's TLS setup cannot be automated without embedding a static self-signed cert (which would be a security smell). The one-time `generate-indexer-certs.yml` run is unavoidable. This is the same process Wazuh's own official quickstart uses.

### 2. Memory requirements
The Wazuh indexer (OpenSearch) requires at minimum 1 GB RAM; the full stack comfortably needs 4 GB. On machines with <4 GB free, the indexer will OOM. The `OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m` setting in docker-compose.yml is already tuned to the minimum viable heap.

### 3. The NAS log file is read-only (one-way)
Wazuh reads `security_events.jsonl` but does not write back to it. There is no loop or feedback between Wazuh actions and the NAS response engine — they are parallel monitoring systems.

### 4. Active response is disabled
Wazuh's active-response module (which can run `iptables` rules, block IPs via firewall) is **not configured** and will not interfere with the NAS response engine. This is intentional — Phase 4 of the NAS build plan already handles enforcement.

### 5. No Wazuh agent deployed
This setup uses **serverless log monitoring** (Wazuh manager reads a mounted file directly). No Wazuh agent binary is installed on the host machine. For full host-level monitoring (syscall auditing, FIM on the host, etc.), you would additionally install the Wazuh agent on the host and enroll it at port 1515. That is beyond the scope of Phase 14 but straightforward to add.

---

## File layout

```
wazuh/
├── generate-indexer-certs.yml       # Cert generator compose file
├── config/
│   ├── certs.yml                    # Certificate node definitions
│   ├── wazuh_cluster/
│   │   └── wazuh_manager.conf       # Custom ossec.conf (with NAS localfile)
│   └── wazuh_indexer_ssl_certs/     # Generated at setup time (gitignored)
│       ├── root-ca.pem
│       ├── root-ca-manager.pem
│       ├── admin.pem / admin-key.pem
│       ├── wazuh.indexer.pem / key
│       ├── wazuh.manager.pem / key
│       └── wazuh.dashboard.pem / key
├── decoders/
│   └── custom_nas.xml               # JSON decoder for security_events.jsonl
└── rules/
    └── custom_nas_rules.xml         # Custom alert rules (IDs 100001–100007)
```
