# policy.py
# This file contains the policy engine for determining the appropriate response to a given risk.

def evaluate_policy(ip: str, risk: dict, correlations: list):
    """
    Evaluate the policy based on the risk score and severity.
    """
    # Get the risk score and severity from the risk dictionary.
    risk_score = risk.get("risk_score", 0)
    severity = risk.get("severity", "low")

    # If the severity is critical, the decision is to block the IP.
    if severity == "critical":
        return {
            "decision": "block",
            "reason": "Critical risk detected",
            "actions": ["block_ip"]
        }

    # If the severity is high, the decision is to throttle the IP.
    if severity == "high":
        return {
            "decision": "throttle",
            "reason": "High risk activity",
            "actions": ["rate_limit"]
        }

    # If the severity is medium, the decision is to monitor the IP.
    if severity == "medium":
        return {
            "decision": "monitor",
            "reason": "Suspicious behavior",
            "actions": []
        }

    # Otherwise, the decision is to allow the IP.
    return {
        "decision": "allow",
        "reason": "Low risk",
        "actions": []
    }