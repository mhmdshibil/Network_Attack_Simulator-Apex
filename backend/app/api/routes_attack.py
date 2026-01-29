# routes_attack.py
# This file defines the API routes for attack detection and management.
# It includes endpoints for getting detections, running the detection engine, and getting blocked IPs.

from fastapi import APIRouter
import pandas as pd
from backend.app.services.detection_service import DetectionEngine
from backend.app.core.paths import DETECTIONS_FILE

# Create a new router for the attack endpoints.
router = APIRouter(prefix="/api", tags=["attacks"])


@router.get("/detections")
def get_detections(limit: int = 50):
    """
    Get the latest attack detections.
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
    Run the detection engine to identify new attacks.
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
    Get a list of all IP addresses that have been blocked.
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