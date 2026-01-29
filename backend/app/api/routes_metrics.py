# routes_metrics.py
# This file defines the API routes for performance and system metrics.
# It includes endpoints for getting general metrics and a timeline of detections.

from fastapi import APIRouter
import pandas as pd

from backend.app.core.paths import DETECTIONS_FILE

# Create a new router for the metrics endpoints.
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/")
def get_metrics():
    """
    Get a summary of system metrics.
    """
    # If the detections file doesn't exist, return a default set of metrics.
    if not DETECTIONS_FILE.exists():
        return {
            "total_detections": 0,
            "unique_blocked_ips": 0,
            "by_label": {},
            "last_detection": None
        }

    # Read the detections data from the CSV file.
    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    # Check if the required columns are present in the DataFrame.
    required_cols = {"ip", "timestamp", "label", "action"}
    if not required_cols.issubset(df.columns):
        return {
            "total_detections": 0,
            "unique_blocked_ips": 0,
            "by_label": {},
            "last_detection": None,
            "error": "invalid_schema"
        }

    # If the DataFrame is empty, return a default set of metrics.
    if df.empty:
        return {
            "total_detections": 0,
            "unique_blocked_ips": 0,
            "by_label": {},
            "last_detection": None
        }

    # Convert the timestamp column to datetime objects.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Create time buckets for aggregating detections over time.
    df["time_bucket"] = df["timestamp"].dt.floor("5s")

    # Group detections by time bucket.
    detections_over_time = (
        df.groupby("time_bucket")
          .size()
          .astype(int)
          .to_dict()
    )

    # Convert the timestamp keys to strings.
    detections_over_time = {str(k): v for k, v in detections_over_time.items()}

    # Calculate various metrics.
    total_detections = len(df)
    unique_blocked_ips = df[df["action"] == "blocked"]["ip"].nunique()
    by_label = df["label"].value_counts().to_dict()
    last_detection = df["timestamp"].iloc[-1]

    # Return the calculated metrics.
    return {
        "total_detections": total_detections,
        "unique_blocked_ips": unique_blocked_ips,
        "by_label": by_label,
        "last_detection": last_detection,
        "detections_over_time": detections_over_time
    }

@router.get("/timeline")
def get_timeline(interval: str = "5s"):
    """
    Get a timeline of detections over a specified interval.
    """
    # If the detections file doesn't exist, return an empty timeline.
    if not DETECTIONS_FILE.exists():
        return {"interval": interval, "timeline": {}}

    # Read the detections data from the CSV file.
    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    # Check if the required columns are present in the DataFrame.
    required_cols = {"ip", "timestamp", "label", "action"}
    if not required_cols.issubset(df.columns) or df.empty:
        return {"interval": interval, "timeline": {}}

    # Convert the timestamp column to datetime objects.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # If the DataFrame is empty, return an empty timeline.
    if df.empty:
        return {"interval": interval, "timeline": {}}

    # Set the timestamp as the index of the DataFrame.
    df = df.set_index("timestamp")

    try:
        # Resample the data by the specified interval and count the number of detections.
        timeline = (
            df.resample(interval)
              .size()
              .to_dict()
        )
    except Exception:
        # If the interval is invalid, return an error.
        return {
            "interval": interval,
            "timeline": {},
            "error": "invalid_interval"
        }

    # Format the timeline data into a dictionary with ISO-formatted timestamps.
    timeline = {
        k.isoformat(): v for k, v in timeline.items() if v > 0
    }

    # Return the timeline data.
    return {
        "interval": interval,
        "timeline": timeline
    }