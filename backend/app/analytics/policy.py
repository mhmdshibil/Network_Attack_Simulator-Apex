# backend/app/analytics/policy.py
# This module implements the policy engine, which is responsible for determining the appropriate
# automated response to a given threat level. The `evaluate_policy` function takes the risk profile
# of an IP address and translates its severity level ('critical', 'high', 'medium', 'low') into a
# clear, actionable decision. This engine acts as the bridge between analytics and response, ensuring
# that the system takes consistent and predictable actions based on the perceived risk. The policies
# defined here are straightforward, mapping each severity level to a specific outcome, such as
# blocking, throttling, or monitoring.

def evaluate_policy(ip: str, risk: dict, correlations: list):
    """
    Evaluates the appropriate security policy based on a given risk profile.

    This function takes the risk score and severity for a specific IP and determines the
    correct response according to a predefined policy ruleset. The decision logic is as follows:
    - 'critical' severity -> 'block' decision
    - 'high' severity     -> 'throttle' decision
    - 'medium' severity   -> 'monitor' decision
    - 'low' severity      -> 'allow' decision

    Args:
        ip (str): The IP address being evaluated.
        risk (dict): A dictionary containing the risk profile, including 'risk_score' and 'severity'.
        correlations (list): A list of correlated events that contributed to the risk score.
                             (Note: This parameter is not currently used but is included for future
                              extensibility, allowing for more complex policy decisions based on
                              the nature of the correlated events.)

    Returns:
        dict: A dictionary containing the final decision ('block', 'throttle', 'monitor', 'allow'),
              a human-readable reason for the decision, and a list of specific actions to be taken
              (e.g., 'block_ip', 'rate_limit').
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