# backend/app/response/actions.py

from datetime import datetime, timezone
from typing import Dict


def execute_action(
    *,
    ip: str,
    action: str,
    severity: str,
    risk_score: float
) -> Dict:
    """
    Phase 8 – Simulated enforcement layer
    """

    timestamp = datetime.now(timezone.utc).isoformat()

    if action == "firewall_block":
        return {
            "executed": True,
            "action": "firewall_block",
            "ip": ip,
            "severity": severity,
            "risk_score": risk_score,
            "message": "IP blocked by simulated firewall rule",
            "timestamp": timestamp
        }
    if action == "throttle":
        return {
            "executed": True,
            "action": "throttle",
            "ip": ip,
            "severity": severity,
            "risk_score": risk_score,
            "message": "Traffic rate-limited",
            "timestamp": timestamp
        }
    if action == "log":
        return {
            "executed": True,
            "action": "log",
            "ip": ip,
            "severity": severity,
            "risk_score": risk_score,
            "message": "Event logged for monitoring",
            "timestamp": timestamp
        }

    return {
        "executed": False,
        "action": "noop",
        "ip": ip,
        "severity": severity,
        "risk_score": risk_score,
        "message": "No enforcement action taken",
        "timestamp": timestamp
    }