import json
from pathlib import Path
from typing import Dict

HARD_BLOCK_FILE = Path("data/processed/hard_blocked_ips.json")

def load_hard_blocked_ips():
    if HARD_BLOCK_FILE.exists():
        try:
            return set(json.loads(HARD_BLOCK_FILE.read_text()))
        except Exception:
            return set()
    return set()

def persist_hard_blocked_ips(ips: set):
    HARD_BLOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    HARD_BLOCK_FILE.write_text(json.dumps(sorted(list(ips))))

HARD_BLOCKED_IPS = load_hard_blocked_ips()


def decide_action(
    ip: str,
    risk_score: int,
    confidence: float
) -> Dict:
    """
    Decides on a defensive action by evaluating the given risk score and confidence level for a specific IP address.

    This function serves as the central logic for the system's response mechanism. It takes the analytical outputs
    (risk and confidence) and maps them to one of the following possible actions:
    - MONITOR: The default action for no detected attack. The system will continue to observe the IP without intervention.
    - BLOCK: Applied when any attack is detected, but confidence is below escalation threshold.
    - BLOCK_ESCALATE: The most severe action, taken for repeated or high-confidence attacks.

    Decision thresholds:
    - Any attack detected (risk_score > 0)        -> BLOCK
    - Repeated attacks or confidence >= 0.5       -> BLOCK_ESCALATE
    - No attacks (risk_score == 0)                -> MONITOR

    Args:
        ip (str): The source IP address of the traffic being evaluated.
        risk_score (int): An integer score from 0-100 representing the calculated risk level.
        confidence (float): A float from 0.0-1.0 indicating the confidence in the risk assessment.

    Returns:
        Dict: A dictionary containing the IP address, original risk and confidence scores, the final decision,
              and a human-readable reason for the decision. The confidence score is rounded to two decimal places.
    """

    if ip in HARD_BLOCKED_IPS:
        return {
            "ip": ip,
            "risk_score": max(risk_score, 100),
            "confidence": round(max(confidence, 0.9), 2),
            "decision": "BLOCK",
            "reason": "IP previously hard-blocked (hard-lock enforcement)"
        }

    # Decision logic per new thresholds
    if risk_score == 0:
        decision = "MONITOR"
        reason = "No malicious activity detected"

    elif risk_score > 0 and confidence < 0.5:
        decision = "BLOCK"
        HARD_BLOCKED_IPS.add(ip)
        persist_hard_blocked_ips(HARD_BLOCKED_IPS)
        reason = "Attack detected — immediate block enforced"

    else:
        decision = "BLOCK_ESCALATE"
        HARD_BLOCKED_IPS.add(ip)
        persist_hard_blocked_ips(HARD_BLOCKED_IPS)
        reason = "Repeated or high-confidence attack — escalated hard block"

    return {
        "ip": ip,
        "risk_score": risk_score,
        "confidence": round(confidence, 2),
        "decision": decision,
        "reason": reason
    }