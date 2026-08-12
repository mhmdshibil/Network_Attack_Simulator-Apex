from fastapi import APIRouter, Depends
from datetime import datetime, timezone
import json
import csv

from backend.app.core.paths import (
    DATA_DIR,
    HARD_BLOCKED_IPS_FILE,
    DECISION_AUDIT_FILE,
    DETECTIONS_FILE,
)
from backend.app.core.auth import require_analyst, require_admin


router = APIRouter(
    prefix="/api/system",
    tags=["system"]
)


# ============================================================
# SYSTEM OVERVIEW
# ============================================================

@router.get("/overview")
def system_overview(_: dict = Depends(require_analyst)):

    hard_block_file = HARD_BLOCKED_IPS_FILE
    audit_file = DECISION_AUDIT_FILE

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
def system_metrics(_: dict = Depends(require_analyst)):

    audit_file = DECISION_AUDIT_FILE
    hard_block_file = HARD_BLOCKED_IPS_FILE

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
def blocked_ips(_: dict = Depends(require_analyst)):

    detections_file = DETECTIONS_FILE

    blocked_list = []

    try:
        with open(detections_file) as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 4:
                    continue

                ip    = row[0]
                ts    = row[1]
                label = row[2]
                action = row[3]

                # Skip header row if present
                if ip == "ip":
                    continue

                if action != "blocked":
                    continue

                # Column 5 is risk_score — present in new format, absent in old
                try:
                    risk = float(row[4]) if len(row) > 4 and row[4] != "risk_score" else 75.0
                except (ValueError, IndexError):
                    risk = 75.0

                blocked_list.append({
                    "ip_address": ip,
                    "blocked_at": ts,
                    "reason": label,
                    "risk_score": risk,
                })

    except Exception:
        pass

    avg_risk = (
        round(sum(b["risk_score"] for b in blocked_list) / len(blocked_list), 1)
        if blocked_list else 0
    )

    stats = {
        "total_blocked": len(blocked_list),
        "avg_risk_score": avg_risk,
        "last_blocked_at": blocked_list[-1]["blocked_at"] if blocked_list else None,
    }

    return {
        "blocked_ips": blocked_list[-20:],  # last 20
        "stats": stats,
    }


# ============================================================
# SYSTEM RESET
# ============================================================

@router.post("/reset")
def system_reset(_: dict = Depends(require_admin)):

    audit_file = DECISION_AUDIT_FILE
    hard_block_file = HARD_BLOCKED_IPS_FILE

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