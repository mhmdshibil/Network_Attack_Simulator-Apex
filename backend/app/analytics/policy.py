def evaluate_policy(ip: str, risk: dict, correlations: list):
    risk_score = risk.get("risk_score", 0)
    severity = risk.get("severity", "low")

    if severity == "critical":
        return {
            "decision": "block",
            "reason": "Critical risk detected",
            "actions": ["block_ip"]
        }

    if severity == "high":
        return {
            "decision": "throttle",
            "reason": "High risk activity",
            "actions": ["rate_limit"]
        }

    if severity == "medium":
        return {
            "decision": "monitor",
            "reason": "Suspicious behavior",
            "actions": []
        }

    return {
        "decision": "allow",
        "reason": "Low risk",
        "actions": []
    }