# backend/app/api/routes_analytics.py

from fastapi import APIRouter, Depends, Query
import pandas as pd
from datetime import datetime, timezone
from backend.app.core.paths import DETECTIONS_FILE
from backend.app.analytics.correlation import correlate_attacks
from backend.app.analytics.risk import compute_risk
from backend.app.core.auth import require_analyst

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

INTERVAL_MAP = {
    "1m": "1min",
    "5m": "5min",
    "10m": "10min",
    "30m": "30min",
    "1h": "1H"
}


# -----------------------------------------------------------
# TOP ATTACKERS
# -----------------------------------------------------------

@router.get("/top_attackers")
def get_top_attackers(limit: int = Query(5, ge=1, le=100), _: dict = Depends(require_analyst)):

    if not DETECTIONS_FILE.exists():
        return {"limit": limit, "attackers": []}

    df = pd.read_csv(
        DETECTIONS_FILE,
        usecols=["ip", "timestamp", "label", "action"]
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])

    cutoff = datetime.now(timezone.utc) - pd.Timedelta(hours=24)
    df = df[df["timestamp"] >= cutoff]

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

    attackers = []

    for _, row in grouped.iterrows():
        attackers.append({
            "ip": row["ip"],
            "count": int(row["count"]),
            "first_seen": row["first_seen"].isoformat(),
            "last_seen": row["last_seen"].isoformat()
        })

    return {"limit": limit, "attackers": attackers}


# -----------------------------------------------------------
# ATTACK DISTRIBUTION
# -----------------------------------------------------------

@router.get("/attack_distribution")
def attack_distribution(_: dict = Depends(require_analyst)):

    if not DETECTIONS_FILE.exists():
        return {"total": 0, "distribution": {}}

    df = pd.read_csv(
        DETECTIONS_FILE,
        usecols=["ip", "timestamp", "label", "action"]
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


# -----------------------------------------------------------
# ATTACK TRENDS
# -----------------------------------------------------------

@router.get("/attack_trends")
def attack_trends(
    interval: str = Query("5m"),
    window: str = Query("1h"),
    _: dict = Depends(require_analyst),
):

    if not DETECTIONS_FILE.exists():
        return {"interval": interval, "window": window, "trends": {}}

    df = pd.read_csv(
        DETECTIONS_FILE,
        usecols=["ip", "timestamp", "label", "action"]
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])

    if interval not in INTERVAL_MAP:
        return {"error": "invalid_interval"}

    interval_norm = INTERVAL_MAP[interval]

    cutoff = pd.Timestamp.utcnow() - pd.to_timedelta(window)
    df = df[df["timestamp"] >= cutoff]

    if df.empty:
        return {"interval": interval, "window": window, "trends": {}}

    df = df.set_index("timestamp")

    grouped = (
        df.groupby("label")
        .resample(interval_norm)
        .size()
        .reset_index(name="count")
    )

    trends = {}

    for _, row in grouped.iterrows():

        label = row["label"]

        trends.setdefault(label, {})[
            row["timestamp"].isoformat()
        ] = int(row["count"])

    return {
        "interval": interval,
        "window": window,
        "trends": trends
    }


# -----------------------------------------------------------
# RISK ENGINE
# -----------------------------------------------------------

@router.get("/risk")
def get_risk_scores(window: str = "5m", _: dict = Depends(require_analyst)):

    correlations = correlate_attacks(window=window)

    if not correlations:
        return {"window": window, "count": 0, "risks": []}

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


# -----------------------------------------------------------
# TRAFFIC TIMELINE (THIS FIXES YOUR EMPTY CHART)
# -----------------------------------------------------------

@router.get("/timeline")
def attack_timeline(interval: str = "5m", window: str = "24h", _: dict = Depends(require_analyst)):

    if not DETECTIONS_FILE.exists():
        return {"timeline": []}

    df = pd.read_csv(
        DETECTIONS_FILE,
        usecols=["ip", "timestamp", "label", "action"]
    )

    if df.empty:
        return {"timeline": []}

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])

    cutoff = pd.Timestamp.utcnow() - pd.to_timedelta(window)
    df = df[df["timestamp"] >= cutoff]

    if df.empty:
        return {"timeline": []}

    if interval not in INTERVAL_MAP:
        return {"error": "invalid_interval"}

    interval_norm = INTERVAL_MAP[interval]

    df = df.set_index("timestamp")

    grouped = df.resample(interval_norm).size()

    timeline = []

    for ts, count in grouped.items():

        timeline.append({
            "time": ts.isoformat(),
            "events": int(count),
            "packets": int(count) * 5
        })

    return {
        "window": window,
        "interval": interval,
        "timeline": timeline
    }