from datetime import datetime, timezone
from typing import Dict

from backend.app.response.decision import decide_action
from backend.app.response.actions import execute_action


def evaluate_and_respond(
    *,
    ip: str,
    risk_score: float,
    confidence: float,
    severity: str,
    attack_count: int,
    window: str
) -> Dict:
    """
    Phase 8 entrypoint:
    Analytics → Decision → Action → Response
    """

    decision = decide_action(
        ip=ip,
        attack_count=attack_count,
        risk_score=risk_score,
        confidence=confidence,
        severity=severity
    )

    # 🔑 Map decision → action
    if decision["decision"] == "BLOCK":
        action = "firewall_block"
    elif decision["decision"] == "MONITOR":
        action = "log"
    else:
        action = "noop"

    action_result = execute_action(
        ip=ip,
        action=action
    )

    return {
        "ip": ip,
        "decision": decision["decision"],
        "action": action,
        "severity": decision["severity"],
        "risk_score": decision["risk_score"],
        "confidence": decision["confidence"],
        "attack_count": attack_count,
        "window": window,
        "reason": decision["reason"],
        "action_result": action_result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }