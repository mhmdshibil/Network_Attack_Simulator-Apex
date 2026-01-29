from fastapi import APIRouter
import pandas as pd
from backend.app.services.detection_service import DetectionEngine
from backend.app.core.paths import DETECTIONS_FILE

router = APIRouter(prefix="/api", tags=["attacks"])


@router.get("/detections")
def get_detections(limit: int = 50):
    if not DETECTIONS_FILE.exists():
        return []

    try:
        df = pd.read_csv(
            DETECTIONS_FILE,
            names=["ip", "timestamp", "label", "action"]
        )
        required_cols = {"ip", "timestamp", "label", "action"}
        if not required_cols.issubset(df.columns):
            raise ValueError("Invalid detections.csv schema")
    except Exception:
        return []

    if df.empty:
        return []

    return df.tail(limit).to_dict(orient="records")

@router.post("/detect/run")
def run_detection():
    engine = DetectionEngine()
    detections = engine.run_once()

    return {
        "status": "completed",
        "detections": detections
    }


# New route: GET /blocked_ips
@router.get("/blocked_ips")
def get_blocked_ips():
    if not DETECTIONS_FILE.exists():
        return {
            "blocked_ips": [],
            "count": 0
        }

    try:
        df = pd.read_csv(
            DETECTIONS_FILE,
            names=["ip", "timestamp", "label", "action"]
        )
        required_cols = {"ip", "timestamp", "label", "action"}
        if not required_cols.issubset(df.columns):
            raise ValueError("Invalid detections.csv schema")
    except Exception:
        return {
            "blocked_ips": [],
            "count": 0
        }

    if df.empty or "action" not in df.columns or "ip" not in df.columns:
        return {
            "blocked_ips": [],
            "count": 0
        }

    blocked = (
        df[df["action"] == "blocked"]["ip"]
        .dropna()
        .unique()
        .tolist()
    )

    return {
        "blocked_ips": blocked,
        "count": len(blocked)
    }