# backend/app/analytics/correlation.py
# This module contains the core logic for correlating attack events over a specified time window.
# Its primary function, `correlate_attacks`, reads raw detection data, filters it to a recent
# timeframe, and then groups events by IP address and attack type (label). A key feature of this
# module is its ability to dynamically identify "bursts" of activity by calculating a threshold
# based on the average event count. This allows the system to distinguish between isolated, low-level
# events and concentrated, high-frequency attacks, which is essential for accurate risk assessment.

import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE

# A mapping of user-friendly interval names to pandas frequency strings, used to define the time
# window for correlation. This provides a simple and consistent way to specify the duration for
# analysis across the application.
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
    Correlates attack events within a specified time window to identify patterns and bursts.

    This function reads detection data, filters it to the given time window, and aggregates the
    events by IP address and attack label. It then determines if the activity from a specific IP
    constitutes a "burst" by comparing the event count against a dynamically calculated threshold.
    The threshold is derived from the average event count across all IPs and labels in the window,
    ensuring that it adapts to the overall level of activity.

    Args:
        window (str, optional): A string representing the time window for the correlation analysis.
                                Must be one of the keys in `INTERVAL_MAP`. Defaults to "5m".

    Returns:
        list: A list of dictionaries, where each dictionary represents a correlated event and
              contains the IP, attack label, event count, time window, whether it was a burst,
              and the threshold used. If the input window is invalid or no data is found, it
              returns an empty list.
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