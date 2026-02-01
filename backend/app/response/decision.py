# backend/app/response/decision.py
# This module provides the core logic for the Decision Engine, which is a critical component of the
# network attack simulator. Its primary responsibility is to translate raw analytical data—specifically
# risk scores and confidence levels—into clear, actionable system decisions. By evaluating these inputs
# against a predefined set of thresholds, the engine determines the appropriate response to potential
# security threats, such as monitoring, alerting, or blocking an IP address. This centralized
# decision-making process ensures consistent and predictable behavior across the system, making it
# easier to manage and customize security policies.

from typing import Dict


def decide_action(
    ip: str,
    risk_score: int,
    confidence: float
) -> Dict:
    """
    Decides on a defensive action by evaluating the given risk score and confidence level for a specific IP address.

    This function serves as the central logic for the system's response mechanism. It takes the analytical outputs
    (risk and confidence) and maps them to one of four possible actions:
    - MONITOR: The default action for low-risk activity. The system will continue to observe the IP without intervention.
    - ALERT: Triggered when activity is suspicious but does not meet the threshold for blocking. This allows security
      personnel to review the situation.
    - BLOCK: Applied when there is a strong belief that an attack is occurring. The system will prevent the IP from
      accessing the network.
    - BLOCK_ESCALATE: The most severe action, taken when a critical threat is detected with very high confidence.
      This involves blocking the IP and escalating the incident for immediate review.

    The decision is made based on a tiered threshold system:
    - Risk >= 40 and Confidence >= 0.85 -> BLOCK_ESCALATE
    - Risk >= 30 and Confidence >= 0.7  -> BLOCK
    - Risk >= 20 and Confidence >= 0.5  -> ALERT
    - Risk >= 10 and Confidence >= 0.4  -> ALERT
    - Otherwise                       -> MONITOR

    Args:
        ip (str): The source IP address of the traffic being evaluated.
        risk_score (int): An integer score from 0-100 representing the calculated risk level.
        confidence (float): A float from 0.0-1.0 indicating the confidence in the risk assessment.

    Returns:
        Dict: A dictionary containing the IP address, original risk and confidence scores, the final decision,
              and a human-readable reason for the decision. The confidence score is rounded to two decimal places.
    """

    decision = "MONITOR"
    reason = "Low risk activity"

    if risk_score >= 40 and confidence >= 0.85:
        decision = "BLOCK_ESCALATE"
        reason = "Critical threat with very high confidence"

    elif risk_score >= 30 and confidence >= 0.7:
        decision = "BLOCK"
        reason = "High risk attack with strong confidence"

    elif risk_score >= 20 and confidence >= 0.5:
        decision = "ALERT"
        reason = "Elevated attack behavior detected"

    elif risk_score >= 10 and confidence >= 0.4:
        decision = "ALERT"
        reason = "Suspicious activity with moderate confidence"

    return {
        "ip": ip,
        "risk_score": risk_score,
        "confidence": round(confidence, 2),
        "decision": decision,
        "reason": reason
    }