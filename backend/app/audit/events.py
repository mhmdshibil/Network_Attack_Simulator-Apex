# backend/app/audit/events.py

from datetime import datetime, timezone
from typing import Dict


def build_audit_event(
    *,
    ip: str,
    phase: str,
    window: str,
    risk_score: float,
    confidence: float,
    severity: str,
    decision: str,
    action: str,
    reason: str,
    attack_count: int
) -> Dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "phase": phase,
        "window": window,
        "risk_score": round(risk_score, 2),
        "confidence": round(confidence, 2),
        "severity": severity,
        "decision": decision,
        "action": action,
        "reason": reason,
        "attack_count": attack_count
    }