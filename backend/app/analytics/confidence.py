from datetime import datetime, timezone


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def window_decay(window: str) -> float:
    if window.endswith("m"):
        m = int(window[:-1])
        return 1.0 if m <= 5 else 0.9 if m <= 15 else 0.8
    if window.endswith("h"):
        h = int(window[:-1])
        return 0.8 if h <= 1 else 0.6 if h <= 6 else 0.4
    return 0.5


def compute_confidence(correlations: list, window: str) -> dict:
    if not correlations:
        return {"score": 0.0}

    attack_count = len(correlations)
    labels = {c.get("label") for c in correlations if c.get("label")}
    timestamps = [c.get("timestamp") for c in correlations if c.get("timestamp")]

    # ---- Volume confidence ----
    volume = 1.0 if attack_count >= 5 else 0.7 if attack_count >= 3 else 0.4

    # ---- Diversity confidence ----
    diversity = 1.0 if len(labels) >= 3 else 0.6 if len(labels) == 2 else 0.3

    # ---- Recency confidence ----
    recency = 0.4
    if timestamps:
        now = datetime.now(timezone.utc)
        ages = []
        for ts in timestamps:
            try:
                t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                ages.append((now - t).total_seconds())
            except Exception:
                pass

        if ages:
            avg = sum(ages) / len(ages)
            recency = 1.0 if avg <= 300 else 0.7 if avg <= 3600 else 0.4

    base = (
        volume * 0.45 +
        diversity * 0.30 +
        recency * 0.25
    )

    win_factor = window_decay(window)

    final = round(clamp(base * win_factor, hi=0.95), 2)

    return {"score": final}