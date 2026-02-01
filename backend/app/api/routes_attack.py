# backend/app/api/routes_attack.py
# This module defines the API routes related to attack detection and management. It provides endpoints
# for retrieving detection data, triggering the detection engine, and querying for blocked IP addresses.
# By centralizing these attack-focused routes, the module offers a clear and organized interface for
# interacting with the core security functions of the application.

from fastapi import APIRouter
import pandas as pd
from backend.app.services.detection_service import DetectionEngine
from backend.app.core.paths import DETECTIONS_FILE

# Create a new router for the attack-related endpoints. This helps in organizing the API and applies
# a consistent prefix and tag to all routes defined in this module.
router = APIRouter(prefix="/api", tags=["attacks"])


@router.get("/detections")
def get_detections(limit: int = 50):
    """
    Retrieves the latest attack detection records from the system.

    This endpoint reads the `detections.csv` file, which serves as the log for all recorded
    malicious activities. It returns a list of the most recent detections, with the number of
    records controlled by the `limit` parameter.

    Args:
        limit (int, optional): The maximum number of detection records to return. Defaults to 50.

    Returns:
        list: A list of dictionaries, where each dictionary represents a single detection event.
              Returns an empty list if the detection file does not exist or is empty.
    """
    # If the detections file doesn't exist, return an empty list.
    if not DETECTIONS_FILE.exists():
        return []

    try:
        # Read the detections data from the CSV file.
        df = pd.read_csv(
            DETECTIONS_FILE,
            names=["ip", "timestamp", "label", "action"]
        )
        # Check if the required columns are present in the DataFrame.
        required_cols = {"ip", "timestamp", "label", "action"}
        if not required_cols.issubset(df.columns):
            raise ValueError("Invalid detections.csv schema")
    except Exception:
        # If there's an error reading the file, return an empty list.
        return []

    # If the DataFrame is empty, return an empty list.
    if df.empty:
        return []

    # Return the last 'limit' detections as a list of dictionaries.
    return df.tail(limit).to_dict(orient="records")

@router.post("/detect/run")
def run_detection():
    """
    Manually triggers a single run of the attack detection engine.

    This endpoint initializes the `DetectionEngine` and executes its `run_once` method. This is
    useful for on-demand analysis or for scenarios where detection is not running continuously.
    The endpoint returns a status message and the number of new detections found during the run.

    Returns:
        dict: A dictionary containing the completion status and the total number of new detections.
    """
    # Create an instance of the detection engine.
    engine = DetectionEngine()
    # Run the detection engine once.
    detections = engine.run_once()

    # Return the status and the number of detections.
    return {
        "status": "completed",
        "detections": detections
    }


# New route: GET /blocked_ips
@router.get("/blocked_ips")
def get_blocked_ips():
    """
    Retrieves a list of all unique IP addresses that have been blocked.

    This endpoint queries the `detections.csv` file to find all records where the 'action'
    is marked as 'blocked'. It then compiles and returns a list of the unique IP addresses
    associated with these actions, along with the total count.

    Returns:
        dict: A dictionary containing a list of unique blocked IPs and the total count.
    """
    # If the detections file doesn't exist, return an empty list.
    if not DETECTIONS_FILE.exists():
        return {
            "blocked_ips": [],
            "count": 0
        }

    try:
        # Read the detections data from the CSV file.
        df = pd.read_csv(
            DETECTIONS_FILE,
            names=["ip", "timestamp", "label", "action"]
        )
        # Check if the required columns are present in the DataFrame.
        required_cols = {"ip", "timestamp", "label", "action"}
        if not required_cols.issubset(df.columns):
            raise ValueError("Invalid detections.csv schema")
    except Exception:
        # If there's an error reading the file, return an empty list.
        return {
            "blocked_ips": [],
            "count": 0
        }

    # If the DataFrame is empty or the required columns are not present, return an empty list.
    if df.empty or "action" not in df.columns or "ip" not in df.columns:
        return {
            "blocked_ips": [],
            "count": 0
        }

    # Filter the DataFrame to get the unique IP addresses that have been blocked.
    blocked = (
        df[df["action"] == "blocked"]["ip"]
        .dropna()
        .unique()
        .tolist()
    )

    # Return the list of blocked IPs and the count.
    return {
        "blocked_ips": blocked,
        "count": len(blocked)
    }