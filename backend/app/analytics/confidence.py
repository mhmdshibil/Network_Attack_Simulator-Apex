# backend/app/analytics/confidence.py
# This module implements the Dynamic Confidence Engine, a system designed to assess the reliability of
# correlated attack data. Its primary function, `compute_confidence`, evaluates a set of correlated
# attack events and produces a confidence score from 0.0 to 1.0. This score indicates how certain the
# system is that the observed activity is a genuine threat. The engine considers multiple factors,
# including the volume of events, the diversity of attack types, the timing of the events (recency and
# temporal spread), and whether the activity occurred in a burst. By synthesizing these factors, the
# engine provides a nuanced and context-aware confidence level, which is critical for making
# accurate security decisions.

from typing import List, Dict
from datetime import datetime, timezone


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """
    Clamps a floating-point value to a specified range [lo, hi].

    This is a utility function to ensure that a value remains within a predefined boundary.
    It is used to keep confidence scores and their factors within the standard 0.0 to 1.0 range.

    Args:
        v (float): The value to clamp.
        lo (float, optional): The lower bound of the range. Defaults to 0.0.
        hi (float, optional): The upper bound of the range. Defaults to 1.0.

    Returns:
        float: The clamped value.
    """
    return max(lo, min(v, hi))


def window_decay(window: str) -> float:
    """
    Calculates a decay factor based on the size of the analysis window.

    The principle is that longer time windows can introduce more noise, so the confidence score
    is slightly reduced to account for this potential uncertainty. Shorter, more focused windows
    receive a higher confidence multiplier.

    Args:
        window (str): A string representing the time window (e.g., "5m", "1h").

    Returns:
        float: A decay factor between 0.5 and 1.0.
    """
    if window.endswith("m"):
        m = int(window[:-1])
        return 1.0 if m <= 5 else 0.9 if m <= 15 else 0.8

    if window.endswith("h"):
        h = int(window[:-1])
        return 0.85 if h <= 1 else 0.7 if h <= 6 else 0.5

    return 0.6


def recency_factor(timestamps: List[str]) -> float:
    """
    Calculates a factor based on the average age of the timestamps.

    This function rewards more recent events with a higher score, as they are more likely to
    be relevant to the current state of the system. The age of an event is the time difference
    between now and its timestamp.

    Args:
        timestamps (List[str]): A list of ISO-formatted timestamp strings.

    Returns:
        float: A factor between 0.4 and 1.0, where a higher value indicates greater recency.
    """
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
    """
    Computes a confidence score based on a list of correlated attack events.

    The final score is a weighted average of several factors, each representing a different
    aspect of the attack pattern. The factors are:
    - Volume (30%): The total number of events. More events increase confidence.
    - Burst (25%): Whether any event occurred in a burst. Bursts are a strong indicator of an attack.
    - Diversity (15%): The number of unique attack types (labels). A wider variety of attacks suggests a more sophisticated threat.
    - Temporal Spread (15%): Whether events occurred at different times.
    - Recency (15%): How recently the events occurred.

    The base score is then scaled by a `window_decay` factor to account for the analysis window size.

    Args:
        correlations (List[Dict]): A list of correlated attack events.
        window (str): The time window used for the analysis.

    Returns:
        Dict: A dictionary containing the final confidence score and a breakdown of the contributing factors.
    """
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