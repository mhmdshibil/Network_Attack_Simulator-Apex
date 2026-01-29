from typing import List, Dict


LABEL_WEIGHTS = {
    "port_scan": 1.0,
    "bruteforce": 1.5,
    "ddos": 2.0,
    "malware": 2.5
}


def compute_risk(correlations: List[Dict]) -> List[Dict]:
    risk_map: Dict[str, Dict] = {}

    for item in correlations:
        ip = item.get("ip")
        label = item.get("label")
        count = item.get("count")
        burst = item.get("burst")

        if ip is None or label is None or count is None:
            continue

        weight = LABEL_WEIGHTS.get(label, 1.0)

        score = count * weight
        if burst:
            score *= 1.5

        if ip not in risk_map:
            risk_map[ip] = {
                "risk_score": 0.0,
                "events": []
            }

        risk_map[ip]["risk_score"] += score
        risk_map[ip]["events"].append({
            "label": label,
            "count": count,
            "burst": bool(burst),
            "score": round(score, 2)
        })

    results: List[Dict] = []
    for ip, data in risk_map.items():
        final_score = min(round(data["risk_score"], 2), 100.0)
        results.append({
            "ip": ip,
            "risk_score": final_score,
            "severity": _severity(final_score),
            "details": data["events"]
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