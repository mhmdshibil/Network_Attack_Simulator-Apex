"""
Campaign API — Phase 5B.

GET  /api/campaigns                 — list (status filter, limit)
GET  /api/campaigns/active          — active only (dashboard live count)
GET  /api/campaigns/stats           — aggregate stats
GET  /api/campaigns/{campaign_id}   — full detail + attack timeline
POST /api/campaigns/{campaign_id}/resolve — manually complete a campaign

/active and /stats are declared BEFORE /{campaign_id} to avoid path-param
capture. All endpoints require analyst auth.
"""
import csv
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_analyst
from backend.app.core.paths import DETECTIONS_FILE

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

try:
    from backend.app.core import database as _db
    from backend.app.core.database import run_async
except Exception:
    _db = None
    run_async = None  # type: ignore[assignment]


def _sweep():
    """Opportunistically complete idle campaigns on read (best-effort)."""
    if _db is None or run_async is None:
        return
    try:
        run_async(_db.complete_stale_campaigns(1800), timeout=5)
    except Exception:
        pass


# ── MUST precede /{campaign_id} ──────────────────────────────────────────────

@router.get("/active")
def active_campaigns(_: dict = Depends(require_analyst)):
    if _db is None or run_async is None:
        return []
    _sweep()
    try:
        return run_async(_db.get_active_campaigns(), timeout=10)
    except Exception:
        return []


@router.get("/stats")
def campaign_stats(_: dict = Depends(require_analyst)):
    empty = {
        "total_campaigns": 0, "active_campaigns": 0, "completed_campaigns": 0,
        "avg_duration_minutes": None, "top_attacker_ip": None, "most_common_type": None,
    }
    if _db is None or run_async is None:
        return empty
    _sweep()
    try:
        return run_async(_db.get_campaign_stats(), timeout=10)
    except Exception:
        return empty


@router.get("")
def list_campaigns(
    status: Optional[str] = None,
    limit: int = 50,
    _: dict = Depends(require_analyst),
):
    if _db is None or run_async is None:
        return []
    _sweep()
    try:
        return run_async(_db.get_campaigns(status=status, limit=limit), timeout=10)
    except Exception:
        return []


@router.get("/{campaign_id}")
def get_campaign_detail(campaign_id: str, _: dict = Depends(require_analyst)):
    if _db is None or run_async is None:
        raise HTTPException(404, "Campaign not found")
    try:
        campaign = run_async(_db.get_campaign(campaign_id), timeout=10)
    except Exception:
        raise HTTPException(404, "Campaign not found")
    if campaign is None:
        raise HTTPException(404, "Campaign not found")

    campaign["timeline"] = _build_timeline(campaign["source_ip"], campaign)
    return campaign


@router.post("/{campaign_id}/resolve")
def resolve_campaign(campaign_id: str, _: dict = Depends(require_analyst)):
    if _db is None or run_async is None:
        raise HTTPException(503, "Database not available")
    now = datetime.now(timezone.utc).isoformat()
    try:
        campaign = run_async(
            _db.update_campaign(campaign_id, status="completed", ended_at=now),
            timeout=10,
        )
    except Exception as exc:
        raise HTTPException(500, f"Resolve failed: {exc}")
    if campaign is None:
        raise HTTPException(404, "Campaign not found")

    # Broadcast the completion so live clients move the card to the table
    try:
        from backend.app.services.ws_manager import manager as ws_manager
        ws_manager.broadcast_sync({
            "type": "campaign_update",
            "campaign_id": campaign["id"],
            "source_ip": campaign["source_ip"],
            "campaign_type": campaign["campaign_type"],
            "stage_count": campaign["stage_count"],
            "attack_sequence": campaign["attack_types"],
            "attack_types": campaign["attack_types"],
            "mitre_stages": campaign["mitre_stages"],
            "severity": campaign["severity"],
            "status": campaign["status"],
            "total_detections": campaign["total_detections"],
            "geo_country": campaign.get("geo_country"),
        })
    except Exception:
        pass

    # Clear in-memory link so future detections start a fresh campaign
    try:
        from backend.app.services.campaign_service import campaign_service
        st = campaign_service._ip_state.get(campaign["source_ip"])
        if st and st.get("campaign_id") == campaign["id"]:
            st["campaign_id"] = None
    except Exception:
        pass

    return campaign


def _build_timeline(source_ip: str, campaign: dict) -> list:
    """Read detections.csv for this IP within the campaign window."""
    started = campaign.get("started_at")
    timeline = []
    try:
        with open(DETECTIONS_FILE, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("ip") != source_ip:
                    continue
                ts = row.get("timestamp", "")
                if started and ts and ts < started:
                    continue
                timeline.append({
                    "timestamp": ts,
                    "attack_type": row.get("label"),
                    "action": row.get("action"),
                    "risk_score": row.get("risk_score"),
                })
    except FileNotFoundError:
        pass
    except Exception:
        pass
    timeline.sort(key=lambda x: x["timestamp"])
    return timeline
