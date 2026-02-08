import json
from pathlib import Path
from datetime import datetime, timezone

HARD_BLOCK_FILE = Path("backend/app/policy/hard_blocked_ips.json")


def _load_hard_blocked_ips() -> dict:
    if not HARD_BLOCK_FILE.exists():
        HARD_BLOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        HARD_BLOCK_FILE.write_text("{}")
    return json.loads(HARD_BLOCK_FILE.read_text())


def _save_hard_blocked_ips(data: dict):
    HARD_BLOCK_FILE.write_text(json.dumps(data, indent=2))


def decide_action(
    *,
    ip: str,
    attack_count: int,
    risk_score: float,
    confidence: float,
    severity: str  # kept for logging only, NOT trusted
) -> dict:
    """
    Phase 8 — Policy Decision Engine (FINAL, CORRECT)

    Decisions are based on:
    - attack_count
    - risk_score
    - confidence
    Severity is derived, not trusted.
    """

    hard_blocked = _load_hard_blocked_ips()

    # 1️⃣ Already hard-blocked → always block
    if ip in hard_blocked:
        return {
            "decision": "BLOCK",
            "severity": "high",
            "risk_score": max(risk_score, 100),
            "confidence": max(confidence, 0.9),
            "reason": "IP previously hard-blocked"
        }

    # 2️⃣ High attack volume with high confidence → BLOCK
    if attack_count >= 5 and confidence >= 0.7:
        hard_blocked[ip] = {
            "blocked_at": datetime.now(timezone.utc).isoformat(),
            "reason": "high_attack_volume"
        }
        _save_hard_blocked_ips(hard_blocked)

        return {
            "decision": "BLOCK",
            "severity": "high",
            "risk_score": max(risk_score, 80),
            "confidence": confidence,
            "reason": "High attack volume with high confidence"
        }

    # 3️⃣ High risk score with confidence → RATE LIMIT
    if risk_score >= 60 and confidence >= 0.7:
        return {
            "decision": "RATE_LIMIT",
            "severity": "medium",
            "risk_score": risk_score,
            "confidence": confidence,
            "reason": "Sustained high-risk behavior"
        }

    # 4️⃣ Suspicious but not critical → ALERT / MONITOR
    if risk_score >= 30:
        return {
            "decision": "ALERT",
            "severity": "medium",
            "risk_score": risk_score,
            "confidence": confidence,
            "reason": "Suspicious activity detected"
        }

    # 5️⃣ Low risk → ALLOW
    return {
        "decision": "ALLOW",
        "severity": "low",
        "risk_score": risk_score,
        "confidence": confidence,
        "reason": "Low risk activity"
    }