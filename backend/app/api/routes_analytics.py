from fastapi import APIRouter
import pandas as pd
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk

INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H"
}

router = APIRouter(prefix="/api/analytics", tags=["analytics"])



@router.get("/top_attackers")
def get_top_attackers(limit: int = 5):
    if not DETECTIONS_FILE.exists():
        return {"limit": limit, "attackers": []}

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    required_cols = {"ip", "timestamp", "label", "action"}
    if not required_cols.issubset(df.columns) or df.empty:
        return {"limit": limit, "attackers": []}

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return {"limit": limit, "attackers": []}

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

    attackers = [
        {
            "ip": row["ip"],
            "count": int(row["count"]),
            "first_seen": row["first_seen"].isoformat(),
            "last_seen": row["last_seen"].isoformat()
        }
        for _, row in grouped.iterrows()
    ]

    return {
        "limit": limit,
        "attackers": attackers
    }


@router.get("/attack_distribution")
def attack_distribution():
    if not DETECTIONS_FILE.exists():
        return {"total": 0, "distribution": {}}

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    required_cols = {"ip", "timestamp", "label", "action"}
    if df.empty or not required_cols.issubset(df.columns):
        return {"total": 0, "distribution": {}}

    label_counts = df["label"].value_counts()
    total = int(label_counts.sum())

    if total == 0:
        return {"total": 0, "distribution": {}}

    distribution = {}
    for label, count in label_counts.items():
        distribution[label] = {
            "count": int(count),
            "percentage": round((count / total) * 100, 2)
        }

    return {
        "total": total,
        "distribution": distribution
    }


# Attack trends over time endpoint
@router.get("/attack_trends")
def attack_trends(interval: str = "5m", window: str = "1h"):
    if not DETECTIONS_FILE.exists():
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    required_cols = {"ip", "timestamp", "label", "action"}
    if df.empty or not required_cols.issubset(df.columns):
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    if df.empty:
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    # Normalize interval
    interval_input = interval
    if interval in INTERVAL_MAP:
        interval = INTERVAL_MAP[interval]

    # Apply rolling window
    try:
        window_delta = pd.to_timedelta(window)
        cutoff = pd.Timestamp.utcnow() - window_delta
        df = df[df["timestamp"] >= cutoff]
    except Exception:
        return {
            "interval_input": interval_input,
            "interval_normalized": None,
            "window": window,
            "trends": {},
            "error": "invalid_window"
        }

    if df.empty:
        return {
            "interval_input": interval_input,
            "interval_normalized": interval,
            "window": window,
            "trends": {}
        }

    df = df.set_index("timestamp")

    try:
        grouped = (
            df.groupby("label")
            .resample(interval)
            .size()
            .reset_index(name="count")
        )
    except Exception:
        return {
            "interval_input": interval_input,
            "interval_normalized": None,
            "window": window,
            "trends": {},
            "error": "invalid_interval"
        }

    trends = {}
    for _, row in grouped.iterrows():
        if row["count"] == 0:
            continue
        label = row["label"]
        ts = row["timestamp"].isoformat()
        trends.setdefault(label, {})[ts] = int(row["count"])

    return {
        "interval_input": interval_input,
        "interval_normalized": interval,
        "window": window,
        "trends": trends
    }


# Expose risk scores endpoint
@router.get("/risk")
def get_risk_scores(window: str = "5m"):
    correlations = correlate_attacks(window=window)
    risks = compute_risk(correlations)

    return {
        "window": window,
        "count": len(risks),
        "risks": risks
    }