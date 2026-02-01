

def build_explanation(
    ip: str,
    decision: str,
    risk_score: float,
    confidence: float,
    signals: dict
):
    reasons = []

    if decision == "BLOCK":
        reasons.append("Risk score exceeded blocking threshold")
        if confidence >= 0.7:
            reasons.append("High confidence in malicious behavior")
    elif decision == "MONITOR":
        reasons.append("Suspicious behavior detected but below blocking threshold")
    else:
        reasons.append("Activity considered normal")

    detection_count = signals.get("detections_count", 0)
    if detection_count > 5:
        reasons.append("Repeated detections in short time window")

    unique_attacks = signals.get("unique_attack_types", 0)
    if unique_attacks > 1:
        reasons.append("Multiple attack types observed")

    return {
        "ip": ip,
        "decision": decision,
        "risk_score": round(risk_score, 2),
        "confidence": round(confidence, 2),
        "severity": _severity_from_risk(risk_score),
        "explanation": {
            "reasons": reasons,
            "signals": signals
        }
    }


def _severity_from_risk(risk_score: float) -> str:
    if risk_score >= 70:
        return "high"
    if risk_score >= 40:
        return "medium"
    return "low"