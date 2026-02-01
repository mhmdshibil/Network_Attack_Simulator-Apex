# risk.py
# This file contains the logic for computing risk scores based on attack correlations.

from typing import List, Dict
from backend.app.analytics.confidence import compute_confidence

# A dictionary of weights for different attack labels.
LABEL_WEIGHTS = {
    "port_scan": 1.0,
    "bruteforce": 1.5,
    "ddos": 2.0,
    "malware": 2.5
}


def compute_risk(correlations: List[Dict], window: str) -> List[Dict]:
    """
    Compute risk scores for each IP address based on the correlated attack events.
    """
    risk_map: Dict[str, Dict] = {}

    # Iterate over each correlation to calculate a risk score.
    for item in correlations:
        ip = item.get("ip")
        label = item.get("label")
        count = item.get("count")
        burst = item.get("burst")

        if ip is None or label is None or count is None:
            continue

        # Get the weight for the attack label, with a default of 1.0.
        weight = LABEL_WEIGHTS.get(label, 1.0)

        # Calculate the score for the event.
        score = count * weight
        if burst:
            score *= 1.5

        # If the IP is not already in the risk map, add it.
        if ip not in risk_map:
            risk_map[ip] = {
                "risk_score": 0.0,
                "events": []
            }

        # Add the score to the total risk score for the IP.
        risk_map[ip]["risk_score"] += score
        # Add the event details to the list of events for the IP.
        risk_map[ip]["events"].append({
            "label": label,
            "count": count,
            "burst": bool(burst),
            "score": round(score, 2)
        })

    results: List[Dict] = []
    # Process the risk map to create a list of risk results.
    for ip, data in risk_map.items():
        final_score = min(round(data["risk_score"], 2), 100.0)
        confidence = {"score": 0.0, "factors": {}}
        if data["events"]:
            try:
                confidence = compute_confidence(data["events"], window)
            except Exception:
                confidence = {"score": 0.0, "factors": {}}

        # Append the risk result to the list of results.
        results.append({
            "ip": ip,
            "risk_score": final_score,
            "severity": _severity(final_score),
            "confidence": confidence.get("score", 0.0),
            "confidence_factors": confidence.get("factors", {}),
            "details": data["events"]
        })

    # Sort the results by risk score in descending order.
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results





def _severity(score: float) -> str:


    """


    Determine the severity level based on the risk score.


    """


    if score >= 80:


        return "critical"


    if score >= 50:


        return "high"


    if score >= 20:


        return "medium"


    return "low"

