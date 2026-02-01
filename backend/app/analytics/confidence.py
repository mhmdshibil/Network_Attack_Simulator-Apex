# backend/app/analytics/confidence.py
# Phase 6.3 – Dynamic Confidence Engine (Production Grade)

from typing import List, Dict
from datetime import datetime, timezone


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(v, hi))


def window_decay(window: str) -> float:
    if window.endswith("m"):
        m = int(window[:-1])
        return 1.0 if m <= 5 else 0.9 if m <= 15 else 0.8

    if window.endswith("h"):
        h = int(window[:-1])
        return 0.85 if h <= 1 else 0.7 if h <= 6 else 0.5

    return 0.6


def recency_factor(timestamps: List[str]) -> float:
    if not timestamps:
        return 0.4

    now = datetime.now(timezone.utc)
    ages = []

    for ts in timestamps:
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            ages.append((now - t).total_seconds())
        except Exception:
            continue

    if not ages:
        return 0.4

    avg = sum(ages) / len(ages)

    if avg <= 300:
        return 1.0
    if avg <= 3600:
        return 0.8
    if avg <= 21600:
        return 0.6
    return 0.4


def compute_confidence(correlations: List[Dict], window: str) -> Dict:
    if not correlations:
        return {"score": 0.0, "factors": {}}

    # ---- Volume ----
    total = sum(int(c.get("count", 1)) for c in correlations)
    volume = 1.0 if total >= 20 else 0.7 if total >= 10 else 0.4 if total >= 5 else 0.2

    # ---- Burst ----
    burst = 1.0 if any(c.get("burst") for c in correlations) else 0.3

    # ---- Diversity ----
    labels = {c.get("label") for c in correlations if c.get("label")}
    diversity = 1.0 if len(labels) >= 3 else 0.6 if len(labels) == 2 else 0.3

    # ---- Temporal Spread ----
    timestamps = [c.get("timestamp") for c in correlations if c.get("timestamp")]
    temporal = 0.7 if len(set(timestamps)) > 1 else 0.3

    # ---- Recency ----
    recency = recency_factor(timestamps)

    # ---- Base Score ----
    base = (
        volume * 0.30 +
        burst * 0.25 +
        diversity * 0.15 +
        temporal * 0.15 +
        recency * 0.15
    )

    # ---- Window Scaling ----
    win_factor = window_decay(window)
    final = round(clamp(base * win_factor), 2)

    return {
        "score": final,
        "factors": {
            "volume": round(volume, 2),
            "burst": round(burst, 2),
            "diversity": round(diversity, 2),
            "temporal": round(temporal, 2),
            "recency": round(recency, 2),
            "window_factor": round(win_factor, 2)
        }
    }