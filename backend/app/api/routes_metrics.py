from fastapi import APIRouter
import pandas as pd

from backend.app.core.paths import DETECTIONS_FILE

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/")
def get_metrics():
    if not DETECTIONS_FILE.exists():
        return {
            "total_detections": 0,
            "unique_blocked_ips": 0,
            "by_label": {},
            "last_detection": None
        }

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    required_cols = {"ip", "timestamp", "label", "action"}
    if not required_cols.issubset(df.columns):
        return {
            "total_detections": 0,
            "unique_blocked_ips": 0,
            "by_label": {},
            "last_detection": None,
            "error": "invalid_schema"
        }

    if df.empty:
        return {
            "total_detections": 0,
            "unique_blocked_ips": 0,
            "by_label": {},
            "last_detection": None
        }

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    df["time_bucket"] = df["timestamp"].dt.floor("5s")

    detections_over_time = (
        df.groupby("time_bucket")
          .size()
          .astype(int)
          .to_dict()
    )

    detections_over_time = {str(k): v for k, v in detections_over_time.items()}

    total_detections = len(df)
    unique_blocked_ips = df[df["action"] == "blocked"]["ip"].nunique()
    by_label = df["label"].value_counts().to_dict()
    last_detection = df["timestamp"].iloc[-1]

    return {
        "total_detections": total_detections,
        "unique_blocked_ips": unique_blocked_ips,
        "by_label": by_label,
        "last_detection": last_detection,
        "detections_over_time": detections_over_time
    }

@router.get("/timeline")
def get_timeline(interval: str = "5s"):
    if not DETECTIONS_FILE.exists():
        return {"interval": interval, "timeline": {}}

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    required_cols = {"ip", "timestamp", "label", "action"}
    if not required_cols.issubset(df.columns) or df.empty:
        return {"interval": interval, "timeline": {}}

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return {"interval": interval, "timeline": {}}

    df = df.set_index("timestamp")

    try:
        timeline = (
            df.resample(interval)
              .size()
              .to_dict()
        )
    except Exception:
        return {
            "interval": interval,
            "timeline": {},
            "error": "invalid_interval"
        }

    timeline = {
        k.isoformat(): v for k, v in timeline.items() if v > 0
    }

    return {
        "interval": interval,
        "timeline": timeline
    }