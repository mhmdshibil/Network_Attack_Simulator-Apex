"""
Baseline API — Phase 5D.

GET  /api/baseline/status       — learning/active status + per-hour sample counts
GET  /api/baseline/stats/{hour} — feature mean/std for a given hour (0-23)
GET  /api/baseline/alerts       — last 100 baseline deviation alerts (in-memory)
GET  /api/baseline/chart        — 24-hour mean/std series per feature
POST /api/baseline/reset        — clear all baseline data (admin)

/stats/{hour}, /alerts, /chart, /reset precede nothing ambiguous; {hour} is int-typed.
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_analyst, require_admin
from backend.app.services.baseline_service import baseline_service

router = APIRouter(prefix="/api/baseline", tags=["baseline"])


@router.get("/status")
def baseline_status(_: dict = Depends(require_analyst)):
    return baseline_service.get_baseline_status()


@router.get("/stats/{hour}")
def baseline_hour_stats(hour: int, _: dict = Depends(require_analyst)):
    if hour < 0 or hour > 23:
        raise HTTPException(400, "hour must be 0-23")
    return baseline_service.get_hourly_stats(hour)


@router.get("/alerts")
def baseline_alerts(_: dict = Depends(require_analyst)):
    return baseline_service.get_alerts()


@router.get("/chart")
def baseline_chart(_: dict = Depends(require_analyst)):
    return baseline_service.get_chart_data()


@router.post("/reset")
def baseline_reset(_: dict = Depends(require_admin)):
    baseline_service.reset()
    return {"status": "reset", "message": "Baseline cleared — learning restarted"}
