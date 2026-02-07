# backend/app/analytics/risk.py

from collections import defaultdict
from typing import List, Dict
from backend.app.analytics.confidence import compute_confidence

LABEL_WEIGHTS = {
    "port_scan": 1,
    "bruteforce": 2,
    "sql_injection": 4,
    "malware": 5,
    "ddos": 6
}

WINDOW_MULTIPLIERS = {
    "5m": 1.0,
    "30m": 0.9,
    "1h": 0.8,
    "6h": 0.6,
    "24h": 0.4
}


def compute_risk(correlations: List[Dict], window: str) -> List[Dict]:
    if not correlations:
        return []

    window_multiplier = WINDOW_MULTIPLIERS.get(window, 0.5)

    ip_events = defaultdict(list)
    ip_score = defaultdict(float)

    for event in correlations:
        ip = event.get("ip")
        label = event.get("label")
        count = int(event.get("count", 1))
        burst = event.get("burst", False)

        if not ip or not label:
            continue

        weight = LABEL_WEIGHTS.get(label, 1)
        score = count * weight
        if burst:
            score *= 1.25

        score *= window_multiplier

        ip_score[ip] += score
        ip_events[ip].append({
            "label": label,
            "count": count,
            "burst": burst,
            "timestamp": event.get("timestamp"),
            "score": round(score, 2)
        })

    results = []

    for ip, events in ip_events.items():
        raw_score = round(min(ip_score[ip], 100), 2)
        confidence_data = compute_confidence(events, window)

        results.append({
            "ip": ip,
            "risk_score": raw_score,
            "severity": _severity(raw_score),
            "confidence": confidence_data["score"],
            "details": events
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results


def _severity(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 20:
        return "medium"
    return "low"