# backend/app/api/routes_analytics.py

from fastapi import APIRouter
import pandas as pd
from datetime import datetime
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H"
}


@router.get("/top_attackers")
def get_top_attackers(limit: int = 5):
    if not DETECTIONS_FILE.exists():
        return {"limit": limit, "attackers": []}

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    if df.empty:
        return {"limit": limit, "attackers": []}

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

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

    attackers = []
    for _, row in grouped.iterrows():
        attackers.append({
            "ip": row["ip"],
            "count": int(row["count"]),
            "first_seen": row["first_seen"].isoformat(),
            "last_seen": row["last_seen"].isoformat()
        })

    return {"limit": limit, "attackers": attackers}


@router.get("/attack_distribution")
def attack_distribution():
    if not DETECTIONS_FILE.exists():
        return {"total": 0, "distribution": {}}

    df = pd.read_csv(
        DETECTIONS_FILE,
        names=["ip", "timestamp", "label", "action"]
    )

    if df.empty:
        return {"total": 0, "distribution": {}}

    counts = df["label"].value_counts()
    total = int(counts.sum())

    distribution = {}
    for label, count in counts.items():
        distribution[label] = {
            "count": int(count),
            "percentage": round((count / total) * 100, 2)
        }

    return {
        "total": total,
        "distribution": distribution
    }


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

    if df.empty:
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {}
        }

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    if interval in INTERVAL_MAP:
        interval_norm = INTERVAL_MAP[interval]
    else:
        return {
            "interval_input": interval,
            "interval_normalized": None,
            "window": window,
            "trends": {},
            "error": "invalid_interval"
        }

    try:
        cutoff = pd.Timestamp.utcnow() - pd.to_timedelta(window)
        df = df[df["timestamp"] >= cutoff]
    except Exception:
        return {
            "interval_input": interval,
            "interval_normalized": interval_norm,
            "window": window,
            "trends": {},
            "error": "invalid_window"
        }

    if df.empty:
        return {
            "interval_input": interval,
            "interval_normalized": interval_norm,
            "window": window,
            "trends": {}
        }

    df = df.set_index("timestamp")

    grouped = (
        df.groupby("label")
        .resample(interval_norm)
        .size()
        .reset_index(name="count")
    )

    trends = {}
    for _, row in grouped.iterrows():
        if row["count"] == 0:
            continue
        trends.setdefault(row["label"], {})[
            row["timestamp"].isoformat()
        ] = int(row["count"])

    return {
        "interval_input": interval,
        "interval_normalized": interval_norm,
        "window": window,
        "trends": trends
    }


@router.get("/risk")
def get_risk_scores(window: str = "5m"):
    correlations = correlate_attacks(window=window)

    print("\n=== DEBUG correlate_attacks OUTPUT ===")
    for c in correlations:
        print(c)
    print("=== END DEBUG ===\n")

    risk_results = compute_risk(correlations, window)

    risks = []
    for r in risk_results:
        details = r.get("details", [])

        attack_count = sum(
            int(e.get("count", 1)) for e in details
        )

        risks.append({
            "ip": r.get("ip"),
            "risk_score": r.get("risk_score", 0.0),
            "severity": r.get("severity", "low"),
            "confidence": r.get("confidence", 0.0),
            "attack_count": attack_count
        })

    return {
        "window": window,
        "count": len(risks),
        "risks": risks
    }