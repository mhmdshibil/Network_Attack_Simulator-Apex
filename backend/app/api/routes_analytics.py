# routes_analytics.py
# This file defines the API routes for the analytics features of the application.
# It includes endpoints for getting top attackers, attack distribution, attack trends, and risk scores.

from fastapi import APIRouter
import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk

# A mapping of friendly interval names to pandas frequency strings.
INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H"
}

# Create a new router for the analytics endpoints.
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/top_attackers")
def get_top_attackers(limit: int = 5):
    """
    Get the top attackers based on the number of detected attacks.
    """
    # If the detections file doesn't exist, return an empty list of attackers.
    if not DETECTIONS_FILE.exists():
        return {"limit": limit, "attackers": []}

    # Read the detections data from the CSV file.
    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    # Check if the required columns are present in the DataFrame.
    required_cols = {"ip", "timestamp", "label", "action"}
    if not required_cols.issubset(df.columns) or df.empty:
        return {"limit": limit, "attackers": []}

    # Convert the timestamp column to datetime objects.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # If the DataFrame is empty after cleaning, return an empty list.
    if df.empty:
        return {"limit": limit, "attackers": []}

    # Group the data by IP address and aggregate the results.
    grouped = (
        df.groupby("ip")
        .agg(
            count=("ip", "size"),
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max")
        )
        .reset_index()
        .sort_values("count", ascending=False)
        .head(limit)
    )

    # Format the aggregated data into a list of dictionaries.
    attackers = [
        {
            "ip": row["ip"],
            "count": int(row["count"]),
            "first_seen": row["first_seen"].isoformat(),
            "last_seen": row["last_seen"].isoformat()
        }
        for _, row in grouped.iterrows()
    ]

    # Return the list of top attackers.
    return {
        "limit": limit,
        "attackers": attackers
    }


@router.get("/attack_distribution")
def attack_distribution():
    """
    Get the distribution of attack labels.
    """
    # If the detections file doesn't exist, return an empty distribution.
    if not DETECTIONS_FILE.exists():
        return {"total": 0, "distribution": {}}

    # Read the detections data from the CSV file.
    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    # Check if the required columns are present in the DataFrame.
    required_cols = {"ip", "timestamp", "label", "action"}
    if df.empty or not required_cols.issubset(df.columns):
        return {"total": 0, "distribution": {}}

    # Count the occurrences of each attack label.
    label_counts = df["label"].value_counts()
    total = int(label_counts.sum())

    # If there are no attacks, return an empty distribution.
    if total == 0:
        return {"total": 0, "distribution": {}}

    # Calculate the percentage of each attack label.
    distribution = {}
    for label, count in label_counts.items():
        distribution[label] = {
            "count": int(count),
            "percentage": round((count / total) * 100, 2)
        }

    # Return the attack distribution.
    return {
        "total": total,
        "distribution": distribution
    }


# Attack trends over time endpoint
@router.get("/attack_trends")
def attack_trends(interval: str = "5m", window: str = "1h"):
    """
    Get the trends of attacks over time.
    """
    # If the detections file doesn't exist, return empty trends.
    if not DETECTIONS_FILE.exists():
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    # Read the detections data from the CSV file.
    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    # Check if the required columns are present in the DataFrame.
    required_cols = {"ip", "timestamp", "label", "action"}
    if df.empty or not required_cols.issubset(df.columns):
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    # Convert the timestamp column to datetime objects.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # If the DataFrame is empty after cleaning, return empty trends.
    if df.empty:
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    # Normalize the interval input to a pandas frequency string.
    interval_input = interval
    if interval in INTERVAL_MAP:
        interval = INTERVAL_MAP[interval]

    # Apply a rolling window to the data to limit the time frame.
    try:
        window_delta = pd.to_timedelta(window)
        cutoff = pd.Timestamp.utcnow() - window_delta
        df = df[df["timestamp"] >= cutoff]
    except Exception:
        # If the window is invalid, return an error.
        return {
            "interval_input": interval_input,
            "interval_normalized": None,
            "window": window,
            "trends": {},
            "error": "invalid_window"
        }

    # If the DataFrame is empty after applying the window, return empty trends.
    if df.empty:
        return {
            "interval_input": interval_input,
            "interval_normalized": interval,
            "window": window,
            "trends": {}
        }

    # Set the timestamp as the index of the DataFrame.
    df = df.set_index("timestamp")

    # Group the data by label and resample by the specified interval.
    try:
        grouped = (
            df.groupby("label")
            .resample(interval)
            .size()
            .reset_index(name="count")
        )
    except Exception:
        # If the interval is invalid, return an error.
        return {
            "interval_input": interval_input,
            "interval_normalized": None,
            "window": window,
            "trends": {},
            "error": "invalid_interval"
        }

    # Format the trends data into a dictionary.
    trends = {}
    for _, row in grouped.iterrows():
        if row["count"] == 0:
            continue
        label = row["label"]
        ts = row["timestamp"].isoformat()
        trends.setdefault(label, {})[ts] = int(row["count"])

    # Return the attack trends.
    return {
        "interval_input": interval_input,
        "interval_normalized": interval,
        "window": window,
        "trends": trends
    }


# Expose risk scores endpoint
@router.get("/risk")
def get_risk_scores(window: str = "5m"):
    """
    Get risk scores based on correlated attacks.
    """
    # Correlate attacks within the specified time window.
    correlations = correlate_attacks(window=window)
    # Compute risk scores based on the correlations.
    risks = compute_risk(correlations, window)

    # Return the risk scores.
    return {
        "window": window,
        "count": len(risks),
        "risks": risks
    }