# backend/app/response/decision.py

import json
from pathlib import Path
from datetime import datetime

HARD_BLOCK_FILE = Path("data/policy/hard_blocked_ips.json")


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
    confidence: float
) -> dict:
    hard_blocked = _load_hard_blocked_ips()

    # 1️⃣ Already blocked → always block
    if ip in hard_blocked:
        return {
            "ip": ip,
            "decision": "BLOCK",
            "severity": "high",
            "forced": True,
            "risk_score": max(risk_score, 100),
            "confidence": max(confidence, 0.9),
            "reason": "IP previously hard-blocked"
        }

    # 2️⃣ No attacks → monitor
    if attack_count == 0:
        return {
            "ip": ip,
            "decision": "MONITOR",
            "severity": "low",
            "forced": False,
            "risk_score": 0,
            "confidence": round(confidence, 2),
            "reason": "No attacks observed"
        }

    # 3️⃣ Any attack → hard block
    hard_blocked[ip] = {
        "blocked_at": datetime.utcnow().isoformat(),
        "reason": "attack_detected"
    }
    _save_hard_blocked_ips(hard_blocked)

    return {
        "ip": ip,
        "decision": "BLOCK",
        "severity": "high",
        "forced": True,
        "risk_score": max(risk_score, 10),
        "confidence": round(max(confidence, 0.6), 2),
        "reason": "Attack detected — hard block enforced"
    }