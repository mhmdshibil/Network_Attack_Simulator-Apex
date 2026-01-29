import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE


INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H",
    "6h": "6H",
    "12h": "12H"
}


def correlate_attacks(window: str = "5m", burst_threshold: int = 5):
    if window not in INTERVAL_MAP:
        return []

    if not DETECTIONS_FILE.exists():
        return []

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    if df.empty:
        return []

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return []

    window_td = pd.to_timedelta(INTERVAL_MAP[window])
    cutoff = pd.Timestamp.utcnow() - window_td
    df = df[df["timestamp"] >= cutoff]

    if df.empty:
        return []

    grouped = (
        df.groupby(["ip", "label"])
        .size()
        .reset_index(name="count")
    )

    correlations = []
    for _, row in grouped.iterrows():
        count = int(row["count"])
        correlations.append({
            "ip": row["ip"],
            "label": row["label"],
            "count": count,
            "window": window,
            "burst": count >= burst_threshold
        })

    return correlations