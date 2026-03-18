from fastapi import APIRouter
from datetime import datetime, timezone
import json
import csv

from backend.app.core.paths import DATA_DIR


router = APIRouter(
    prefix="/api/system",
    tags=["system"]
)


# ============================================================
# SYSTEM OVERVIEW
# ============================================================

@router.get("/overview")
def system_overview():

    hard_block_file = DATA_DIR / "policies" / "hard_blocked_ips.json"
    audit_file = DATA_DIR / "audit" / "decision_audit.csv"

    now = datetime.now(timezone.utc)
    window_minutes = 5

    try:
        with open(hard_block_file) as f:
            hard_blocked = json.load(f)
            if not isinstance(hard_blocked, dict):
                hard_blocked = {}
    except Exception:
        hard_blocked = {}

    blocked_ips = len(hard_blocked)

    rate_limited_ips = set()
    monitoring_ips = set()
    active_attackers = set()

    try:
        with open(audit_file) as f:
            reader = csv.DictReader(f)

            for row in reader:
                ip = row.get("ip", "")
                decision = row.get("decision", "")
                ts = row.get("timestamp", "")

                if not ip or not ts:
                    continue

                try:
                    event_time = datetime.fromisoformat(ts)
                except Exception:
                    continue

                if (now - event_time).total_seconds() > window_minutes * 60:
                    continue

                active_attackers.add(ip)

                if decision == "RATE_LIMIT":
                    rate_limited_ips.add(ip)
                elif decision == "MONITOR":
                    monitoring_ips.add(ip)

    except Exception:
        pass

    threat_score = (
        len(active_attackers)
        + 2 * len(rate_limited_ips)
        + 3 * blocked_ips
    )

    if threat_score >= 20:
        threat_level = "CRITICAL"
    elif threat_score >= 10:
        threat_level = "HIGH"
    elif threat_score >= 3:
        threat_level = "ELEVATED"
    else:
        threat_level = "LOW"

    return {
        "active_attackers": len(active_attackers),
        "blocked_ips": blocked_ips,
        "rate_limited_ips": len(rate_limited_ips),
        "monitoring_ips": len(monitoring_ips),
        "threat_level": threat_level,
        "window": f"{window_minutes}m",
        "timestamp": now.isoformat()
    }


# ============================================================
# HEALTH ENDPOINTS
# ============================================================

@router.get("/health")
def system_health():

    return {
        "status": "ok",
        "service": "network-defense-simulator",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/liveness")
def system_liveness():

    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/readiness")
def system_readiness():

    policies_dir = DATA_DIR / "policies"
    audit_dir = DATA_DIR / "audit"

    ready = policies_dir.exists() and audit_dir.exists()

    return {
        "ready": ready,
        "policies_available": policies_dir.exists(),
        "audit_storage_available": audit_dir.exists(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# SYSTEM METRICS
# ============================================================

@router.get("/metrics")
def system_metrics():

    audit_file = DATA_DIR / "audit" / "decision_audit.csv"
    hard_block_file = DATA_DIR / "policies" / "hard_blocked_ips.json"

    total_decisions = 0
    blocked = 0
    rate_limited = 0
    monitored = 0
    last_activity = None

    try:
        with open(audit_file) as f:
            reader = csv.DictReader(f)
            for row in reader:

                total_decisions += 1

                decision = row.get("decision", "")
                ts = row.get("timestamp", "")

                if decision == "BLOCK":
                    blocked += 1
                elif decision == "RATE_LIMIT":
                    rate_limited += 1
                elif decision == "MONITOR":
                    monitored += 1

                if ts:
                    try:
                        t = datetime.fromisoformat(ts)
                        if not last_activity or t > last_activity:
                            last_activity = t
                    except Exception:
                        pass

    except Exception:
        pass

    try:
        with open(hard_block_file) as f:
            hard_blocked = json.load(f)
            active_blocks = len(hard_blocked) if isinstance(hard_blocked, dict) else 0
    except Exception:
        active_blocks = 0

    return {
        "total_decisions": total_decisions,
        "blocked_actions": blocked,
        "rate_limited_actions": rate_limited,
        "monitor_actions": monitored,
        "active_hard_blocks": active_blocks,
        "last_activity": last_activity.isoformat() if last_activity else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# BLOCKED IPS (FOR FRONTEND TABLE)
# ============================================================

@router.get("/blocked_ips")
def blocked_ips():

    detections_file = DATA_DIR / "processed" / "detections.csv"

    blocked_list = []

    try:
        with open(detections_file) as f:
            reader = csv.reader(f)

            for row in reader:

                if len(row) < 4:
                    continue

                ip, ts, label, action = row

                if action != "blocked":
                    continue

                blocked_list.append({
                    "ip_address": ip,
                    "blocked_at": ts,
                    "reason": label,
                    "risk_score": 75.0
                })

    except Exception:
        pass

    stats = {
        "total_blocked": len(blocked_list),
        "avg_risk_score": 75.0 if blocked_list else 0,
        "last_blocked_at": blocked_list[-1]["blocked_at"] if blocked_list else None
    }

    return {
        "blocked_ips": blocked_list[-20:],  # last 20
        "stats": stats
    }


# ============================================================
# SYSTEM RESET
# ============================================================

@router.post("/reset")
def system_reset():

    audit_file = DATA_DIR / "audit" / "decision_audit.csv"
    hard_block_file = DATA_DIR / "policies" / "hard_blocked_ips.json"

    cleared = []

    try:
        with open(audit_file, "w") as f:
            f.write("timestamp,ip,decision,severity,risk_score,confidence,reason\n")
        cleared.append("audit_log")
    except Exception:
        pass

    try:
        with open(hard_block_file, "w") as f:
            json.dump({}, f)
        cleared.append("hard_blocks")
    except Exception:
        pass

    return {
        "status": "reset_complete",
        "cleared": cleared,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }