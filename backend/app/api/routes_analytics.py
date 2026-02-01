# backend/app/api/routes_analytics.py
# This module defines the RESTful API endpoints for the analytics features of the Network Attack Simulator.
# It leverages the FastAPI framework to create a set of routes that expose critical security metrics and
# insights. These endpoints provide access to real-time and historical data, including top attackers,
# attack distribution, temporal attack trends, and calculated risk scores. By encapsulating the analytics
# logic within this API, the system offers a standardized and accessible way for front-end applications
# or other services to consume and visualize security-related data.

from fastapi import APIRouter
import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk

# A mapping of user-friendly interval names to pandas frequency strings. This allows the API to accept
# simple inputs (e.g., "5m") and translate them into a format that pandas can use for time-series resampling.
INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H"
}

# Create a new FastAPI router for the analytics endpoints. This helps organize the routes and allows
# for modular configuration, such as setting a common prefix ("/api/analytics") and tags for all routes defined here.
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/top_attackers")
def get_top_attackers(limit: int = 5):
    """
    Retrieves a list of the top attackers based on the number of detected malicious activities.

    This endpoint reads from the `detections.csv` file, groups the data by IP address, and aggregates
    the information to identify which IPs are responsible for the most attacks. For each top attacker,
    it returns the total attack count, as well as the first and last times they were seen.

    Args:
        limit (int, optional): The maximum number of top attackers to return. Defaults to 5.

    Returns:
        dict: A dictionary containing the query limit and a list of attacker objects.
              Each attacker object includes their IP, attack count, and the timestamps of their
              first and last seen activities. If no detections are found, it returns an empty list.
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
    Calculates and returns the distribution of different attack types (labels).

    This endpoint analyzes the `detections.csv` file to count the occurrences of each unique attack
    label (e.g., "Port Scan", "SQL Injection"). It provides both the raw count for each label and its
    percentage relative to the total number of detected attacks.

    Returns:
        dict: A dictionary containing the total number of attacks and a nested dictionary with the
              distribution details. Each key in the distribution is an attack label, and its value
              is an object with the count and percentage.
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
    Provides time-series data on attack trends, showing how many attacks of each type occurred
    over a specified time window, aggregated into intervals.

    This endpoint reads detection data, filters it to a recent time window, and then groups the
    attacks by label. It resamples the data into time intervals (e.g., every 5 minutes) to show
    how the frequency of each attack type changes over time.

    Args:
        interval (str, optional): The time interval for aggregating attack counts (e.g., "1m", "5m", "1h").
                                  Defaults to "5m".
        window (str, optional): The total time window to consider for the trend analysis (e.g., "1h", "6h").
                                Defaults to "1h".

    Returns:
        dict: A dictionary containing metadata about the query (interval, window) and a `trends` object.
              The `trends` object is a nested dictionary where keys are attack labels, and values are
              dictionaries mapping ISO-formatted timestamps to attack counts.
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
    Computes and returns risk scores for IP addresses based on correlated attack patterns.

    This endpoint first calls the `correlate_attacks` function to identify related malicious
    activities within a given time window. It then passes these correlations to the `compute_risk`
    function to calculate a risk score for each IP address. The resulting scores indicate the
    perceived threat level of each IP.

    Args:
        window (str, optional): The time window to use for correlating attacks, specified in a
                                pandas-compatible format (e.g., "5m", "1h"). Defaults to "5m".

    Returns:
        dict: A dictionary containing the time window, the total count of IPs with risk scores,
              and a list of risk objects. Each risk object details the IP, its calculated risk score,
              and other relevant metadata.
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