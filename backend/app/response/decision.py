import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

def _safe_json_load(path: Path, default):
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(default, indent=2))
            return default
        return json.loads(path.read_text() or json.dumps(default))
    except Exception:
        # Corrupted file fallback
        return default

def _atomic_write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)

def window_to_minutes(window: str) -> float:
    if window.endswith("m"):
        return float(window[:-1])
    if window.endswith("h"):
        return float(window[:-1]) * 60
    return 5.0

HARD_BLOCK_FILE = Path("backend/app/policy/hard_blocked_ips.json")


def _load_hard_blocked_ips() -> dict:
    return _safe_json_load(HARD_BLOCK_FILE, {})


def _save_hard_blocked_ips(data: dict):
    _atomic_write(HARD_BLOCK_FILE, data)


REPUTATION_FILE = Path("data/policies/ip_reputation.json")


def _load_reputation() -> dict:
    return _safe_json_load(REPUTATION_FILE, {})


def _save_reputation(data: dict):
    _atomic_write(REPUTATION_FILE, data)


WHITELIST_FILE = Path("data/policies/whitelist_ips.json")

def _load_whitelist() -> set:
    data = _safe_json_load(WHITELIST_FILE, [])
    return set(data)


# Reputation decay (Step 6)
LAST_SEEN_FILE = Path("data/policies/ip_last_seen.json")

def _load_last_seen() -> dict:
    data = _safe_json_load(LAST_SEEN_FILE, {})
    if isinstance(data, list):
        # Convert accidental list to dict
        data = {}
    return data


def _save_last_seen(data: dict):
    _atomic_write(LAST_SEEN_FILE, data)


def decide_action(
    *,
    ip: str,
    attack_count: int,
    risk_score: float,
    confidence: float,
    severity: str,
    window: str
) -> dict:
    """
    Phase 9 — Escalation-aware policy engine
    """

    # 🟢 Whitelist override (Step 7)
    whitelist = _load_whitelist()

    hard_blocked = _load_hard_blocked_ips()

    # Input sanity guards
    attack_count = max(0, int(attack_count))
    risk_score = max(0.0, float(risk_score))
    confidence = min(max(float(confidence), 0.0), 1.0)

    if ip in whitelist:
        # Soft whitelist: allow but escalate if critical
        if severity == "critical":
            pass
        else:
            return {
                "decision": "ALLOW",
                "severity": "low",
                "risk_score": risk_score,
                "confidence": confidence,
                "reason": "Whitelisted IP"
            }

    # 🔥 Active temporary hard-block check (Step 4)
    if ip in hard_blocked:
        block_info = hard_blocked[ip]

        try:
            blocked_at = datetime.fromisoformat(block_info["blocked_at"])
        except Exception:
            del hard_blocked[ip]
            _save_hard_blocked_ips(hard_blocked)
            blocked_at = datetime.now(timezone.utc)

        duration = timedelta(seconds=block_info.get("duration_sec", 1800))

        now = datetime.now(timezone.utc)
        if now - blocked_at < duration:
            return {
                "decision": "BLOCK",
                "severity": "high",
                "risk_score": max(risk_score, 100),
                "confidence": max(confidence, 0.9),
                "reason": "Active temporary hard-block"
            }

        # ⏳ Block expired → remove IP
        del hard_blocked[ip]
        _save_hard_blocked_ips(hard_blocked)

    # ⚠️ 3) Critical severity still overrides everything
    if severity == "critical":
        hard_blocked[ip] = {
            "blocked_at": datetime.now(timezone.utc).isoformat(),
            "reason": "critical_severity",
            "duration_sec": 3600
        }
        _save_hard_blocked_ips(hard_blocked)

        return {
            "decision": "BLOCK",
            "severity": "high",
            "risk_score": 100,
            "confidence": max(confidence, 0.8),
            "reason": "Critical threat detected"
        }

    # ⏳ Reputation decay based on inactivity (Step 6)
    last_seen_map = _load_last_seen()
    now = datetime.now(timezone.utc)
    last_seen_iso = last_seen_map.get(ip)
    if last_seen_iso:
        try:
            last_seen = datetime.fromisoformat(last_seen_iso)
            hours_idle = (now - last_seen).total_seconds() / 3600.0
            if hours_idle >= 24:
                # decay reputation by 30% per day idle
                reputation_tmp = _load_reputation()
                current = reputation_tmp.get(ip, 0)
                decayed = int(current * 0.7)
                reputation_tmp[ip] = decayed
                _save_reputation(reputation_tmp)
        except Exception:
            pass

    # 🧠 Reputation load
    reputation = _load_reputation()
    score = reputation.get(ip, 0)

    # ⏱️ Time-weighted attack rate
    minutes = window_to_minutes(window)
    attack_rate = attack_count / max(minutes, 1)

    # 📈 Update reputation based on current behavior
    if severity == "high":
        score += 50
    elif severity == "medium":
        score += 20
    elif attack_count >= 5:
        score += 10

    reputation[ip] = min(score, 500)
    _save_reputation(reputation)

    # 🕒 Update last seen (Step 9)
    last_seen_map[ip] = now.isoformat()
    _save_last_seen(last_seen_map)

    # 🚫 Reputation-based immediate block
    if score >= 200:
        return {
            "decision": "BLOCK",
            "severity": "high",
            "risk_score": 100,
            "confidence": 0.95,
            "reason": "IP reputation extremely high"
        }

    # 🔒 1) Already hard-blocked
    if ip in hard_blocked:
        return {
            "decision": "BLOCK",
            "severity": "high",
            "risk_score": max(risk_score, 100),
            "confidence": max(confidence, 0.9),
            "reason": "IP previously hard-blocked"
        }

    # 🔥 2) Rate-based escalation (Time-weighted)
    score = reputation.get(ip, 0)
    
    if attack_rate >= 5:
        hard_blocked[ip] = {
            "blocked_at": datetime.now(timezone.utc).isoformat(),
            "reason": "burst_attack",
            "duration_sec": 1800
        }
        _save_hard_blocked_ips(hard_blocked)

        return {
            "decision": "BLOCK",
            "severity": "high",
            "risk_score": max(risk_score, 90),
            "confidence": max(confidence, 0.85),
            "reason": "Burst attack detected"
        }

    if attack_rate >= 1:
        return {
            "decision": "RATE_LIMIT",
            "severity": "medium",
            "risk_score": risk_score,
            "confidence": confidence,
            "reason": "Elevated attack rate"
        }

    if attack_count >= 5:
        return {
            "decision": "MONITOR",
            "severity": "medium",
            "risk_score": risk_score,
            "confidence": confidence,
            "reason": "Repeated suspicious activity"
        }
    # 🟡 Moderate attack volume → rate limit
    if attack_count >= 10:
        return {
        
            "decision": "RATE_LIMIT",
            "severity": "medium",
            "risk_score": max(risk_score, 70),
            "confidence": max(confidence, 0.7),
            "reason": "High attack volume — throttling traffic"
        }
    # 🟠 Medium severity
    if severity == "medium":
        return {
            "decision": "MONITOR",
            "severity": "medium",
            "risk_score": risk_score,
            "confidence": confidence,
            "reason": "Suspicious activity"
        }

    # 🟢 Low severity
    return {
        "decision": "ALLOW",
        "severity": "low",
        "risk_score": risk_score,
        "confidence": confidence,
        "reason": "Low risk activity"
    }