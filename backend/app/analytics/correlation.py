# correlation.py
# This file contains the logic for correlating attack events.

import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE

# A mapping of friendly interval names to pandas frequency strings.
INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H",
    "6h": "6H",
    "12h": "12H"
}


def correlate_attacks(window: str = "5m"):
    """
    Correlate attack events within a specified time window.
    """
    # If the window is not in the interval map, return an empty list.
    if window not in INTERVAL_MAP:
        return []

    # If the detections file doesn't exist, return an empty list.
    if not DETECTIONS_FILE.exists():
        return []

    # Read the detections data from the CSV file.
    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    # If the DataFrame is empty, return an empty list.
    if df.empty:
        return []

    # Convert the timestamp column to datetime objects.
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # If the DataFrame is empty after cleaning, return an empty list.
    if df.empty:
        return []

    # Filter the data to the specified time window.
    window_td = pd.to_timedelta(INTERVAL_MAP[window])
    cutoff = pd.Timestamp.utcnow() - window_td
    df = df[df["timestamp"] >= cutoff]

    # If the DataFrame is empty after filtering, return an empty list.
    if df.empty:
        return []

    # Group the data by IP and label to count the number of events.
    grouped = (
        df.groupby(["ip", "label"])
        .size()
        .reset_index(name="count")
    )

    # Calculate a dynamic threshold for identifying bursts of activity.
    avg_count = grouped["count"].mean()
    dynamic_threshold = max(2, int(avg_count))

    correlations = []

    # Create a list of correlation dictionaries.
    for _, row in grouped.iterrows():
        count = int(row["count"])

        correlations.append({
            "ip": row["ip"],
            "label": row["label"],
            "count": count,
            "window": window,
            "burst": count >= dynamic_threshold,
            "threshold": dynamic_threshold
        })

    # Return the list of correlations.
    return correlations