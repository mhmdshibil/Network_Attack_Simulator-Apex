from datetime import datetime, timezone
from typing import Dict


def execute_action(*, ip: str, action: str) -> Dict:
    """
    Phase 8 – Enforcement layer (simulated).
    Executes the action decided by the response engine.
    """

    timestamp = datetime.now(timezone.utc).isoformat()

    if action == "firewall_block":
        print(f"[FIREWALL] DROP traffic from {ip}")
        return {
            "executed": True,
            "action": "firewall_block",
            "ip": ip,
            "message": "IP blocked by simulated firewall rule",
            "timestamp": timestamp
        }

    if action == "rate_limit":
        print(f"[RATE_LIMIT] Throttling traffic from {ip}")
        return {
            "executed": True,
            "action": "rate_limit",
            "ip": ip,
            "message": "Traffic rate-limited",
            "timestamp": timestamp
        }

    if action == "alert":
        print(f"[ALERT] Security alert for {ip}")
        return {
            "executed": True,
            "action": "alert",
            "ip": ip,
            "message": "Security alert generated",
            "timestamp": timestamp
        }

    # Default: no action
    return {
        "executed": False,
        "action": "noop",
        "ip": ip,
        "message": "No enforcement action taken",
        "timestamp": timestamp
    }