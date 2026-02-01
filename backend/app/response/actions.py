# backend/app/response/actions.py
# This module serves as the simulated action execution layer for the system's response engine.
# Its primary function, `execute_action`, takes a decision payload and translates it into a series
# of concrete, albeit simulated, system actions. This layer is crucial for demonstrating how the
# system would respond to threats without performing actual, potentially disruptive, actions on the
# host machine. The actions include logging, creating simulated firewall rules, and sending
# notifications, providing a clear and safe way to visualize the system's defensive posture.

from datetime import datetime
from typing import Dict, List


def execute_action(decision_payload: Dict) -> Dict:
    """
    Executes a simulated system action based on the decision from the response engine.

    This function takes a payload containing a decision (e.g., 'MONITOR', 'BLOCK') and simulates
    the corresponding system-level actions. For example, a 'BLOCK' decision will generate a log
    entry and a simulated `iptables` command. This allows the application to demonstrate its
    response capabilities without modifying the actual system configuration.

    Args:
        decision_payload (Dict): A dictionary containing the decision details, including the
                                 'ip' and the 'decision' string.

    Returns:
        Dict: A dictionary containing the original IP and decision, the execution timestamp, and
              a list of strings describing the simulated actions that were taken.
    """

    ip = decision_payload["ip"]
    decision = decision_payload["decision"]

    actions: List[str] = []
    timestamp = datetime.utcnow().isoformat()

    if decision == "MONITOR":
        actions.append(f"[LOG] Monitoring IP {ip}")

    elif decision == "ALERT":
        actions.append(f"[LOG] Alert triggered for IP {ip}")
        actions.append(f"[NOTIFY] SOC notified about suspicious activity")

    elif decision == "BLOCK":
        actions.append(f"[SIMULATED FIREWALL] iptables -A INPUT -s {ip} -j DROP")
        actions.append(f"[LOG] IP {ip} blocked")

    elif decision == "BLOCK_ESCALATE":
        actions.append(f"[SIMULATED FIREWALL] iptables -A INPUT -s {ip} -j DROP")
        actions.append(f"[LOG] IP {ip} blocked")
        actions.append(f"[ESCALATION] Incident escalated to admin/SOC")

    else:
        actions.append(f"[UNKNOWN] No action executed")

    return {
        "ip": ip,
        "decision": decision,
        "executed_at": timestamp,
        "actions": actions
    }