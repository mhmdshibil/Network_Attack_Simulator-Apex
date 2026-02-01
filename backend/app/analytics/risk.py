# backend/app/analytics/risk.py
# This module is responsible for computing risk scores based on correlated attack data. It serves as a
# core component of the analytics engine by translating raw attack events into a quantifiable measure of
# risk. The primary function, `compute_risk`, takes a list of correlated attack events, applies a
# weighted scoring model, and integrates a confidence score to produce a comprehensive risk profile for
#
# each IP address. This allows the system to prioritize threats and make informed decisions.

from typing import List, Dict
from backend.app.analytics.confidence import compute_confidence

# A dictionary that assigns a numerical weight to different types of attacks (labels). These weights
# are used in the risk calculation to ensure that more severe attack types contribute more to the
# overall risk score. For example, 'ddos' is considered more critical than a 'port_scan'.
LABEL_WEIGHTS = {
    "port_scan": 1.0,
    "bruteforce": 1.5,
    "ddos": 2.0,
    "malware": 2.5
}


def compute_risk(correlations: List[Dict], window: str) -> List[Dict]:
    """
    Computes risk scores for each IP address based on a list of correlated attack events.

    This function aggregates attack data for each IP, calculates a preliminary risk score by applying
    weights based on the attack type (`label`) and whether the event was part of a burst. It then
    computes a confidence score for the aggregated events and combines everything into a final risk
    profile for each IP.

    The risk score for a single event is calculated as:
        score = count * weight * (1.5 if burst else 1.0)

    Args:
        correlations (List[Dict]): A list of dictionaries, where each dictionary represents a
                                   correlated attack event and contains details like 'ip', 'label',
                                   'count', and 'burst'.
        window (str): The time window used for the analysis, which is passed to the confidence
                      computation.

    Returns:
        List[Dict]: A list of dictionaries, each representing the risk profile for an IP address.
                    The list is sorted in descending order by risk score. Each profile includes the IP,
                    the final risk score, a severity level, confidence score, and detailed event data.
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
    Determines the severity level based on a given risk score.

    This helper function translates a numerical risk score into a human-readable severity category.
    The categories are 'critical', 'high', 'medium', and 'low', each corresponding to a different
    range of scores.

    Args:
        score (float): The risk score, typically between 0 and 100.

    Returns:
        str: The corresponding severity level as a string.
    """
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 20:
        return "medium"
    return "low"
