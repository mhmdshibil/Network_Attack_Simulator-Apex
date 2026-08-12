# backend/app/response/engine.py

from datetime import datetime, timezone
from typing import Dict

from backend.app.response.decision import decide_action
from backend.app.response.actions import execute_action
from backend.app.audit.events import build_audit_event
from backend.app.audit.writer import write_audit_event


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
    Analytics → Decision → Action → Audit → Response
    """

    decision = decide_action(
        ip=ip,
        attack_count=attack_count,
        risk_score=risk_score,
        confidence=confidence,
        severity=severity,
        window=window
    )

    # Map decision → action (hardened + compatible with actions.py)
    decision_type = decision.get("decision", "ALLOW")

    if decision_type == "BLOCK":
        action = "firewall_block"
    elif decision_type == "RATE_LIMIT":
        action = "throttle"       # now wired correctly
    elif decision_type == "MONITOR":
        action = "log"
    else:
        action = "noop"

    # Defensive field extraction (prevents crashes on malformed decisions)
    severity_val = decision.get("severity", "low")
    risk_val = decision.get("risk_score", risk_score)

    action_result = execute_action(
        ip=ip,
        action=action,
        severity=severity_val,
        risk_score=risk_val
    )

    audit_event = build_audit_event(
        ip=ip,
        phase="9",
        window=window,
        risk_score=decision.get("risk_score", risk_score),
        confidence=decision.get("confidence", confidence),
        severity=decision.get("severity", severity),
        decision=decision.get("decision", "ALLOW"),
        action=action_result.get("action", action),
        reason=decision.get("reason", "No reason provided"),
        attack_count=attack_count
    )

    write_audit_event(audit_event)

    return {
        "ip": ip,
        "decision": decision.get("decision", "ALLOW"),
        "action": action,
        "severity": decision.get("severity", severity),
        "risk_score": decision.get("risk_score", risk_score),
        "confidence": decision.get("confidence", confidence),
        "attack_count": attack_count,
        "window": window,
        "reason": decision.get("reason", "No reason provided"),
        "action_result": action_result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }