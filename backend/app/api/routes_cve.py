"""
CVE API — Phase 5C.

GET  /api/cve/stats               — feed statistics
GET  /api/cve/recent?days=30      — recent CVEs (date_added desc)
GET  /api/cve/match/{attack_type} — top CVEs matching an attack type
POST /api/cve/refresh             — trigger an immediate KEV re-fetch
GET  /api/cve/{cve_id}            — full CVE detail

/stats, /recent, /match, /refresh precede /{cve_id} to avoid path capture.
All require analyst auth (refresh requires analyst too, per spec).
"""
from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_analyst
from backend.app.services.cve_service import cve_service

router = APIRouter(prefix="/api/cve", tags=["cve"])

try:
    from backend.app.core.database import run_async, run_async_bg
except Exception:
    run_async = None       # type: ignore[assignment]
    run_async_bg = None    # type: ignore[assignment]


@router.get("/stats")
def cve_stats(_: dict = Depends(require_analyst)):
    if run_async is None:
        return {"total_cves": 0, "last_updated": None, "ransomware_count": 0,
                "recent_30_days": 0, "top_vendors": []}
    try:
        return run_async(cve_service.get_stats(), timeout=10)
    except Exception:
        return {"total_cves": 0, "last_updated": None, "ransomware_count": 0,
                "recent_30_days": 0, "top_vendors": []}


@router.get("/recent")
def cve_recent(days: int = 30, _: dict = Depends(require_analyst)):
    if run_async is None:
        return []
    try:
        return run_async(cve_service.get_recent_cves(days), timeout=10)
    except Exception:
        return []


@router.get("/match/{attack_type}")
def cve_match(attack_type: str, _: dict = Depends(require_analyst)):
    if run_async is None:
        return []
    try:
        matches = run_async(cve_service.match_detection({"attack_type": attack_type}), timeout=10)
        return [m.as_dict() for m in matches]
    except Exception:
        return []


@router.post("/refresh")
def cve_refresh(_: dict = Depends(require_analyst)):
    """Trigger an immediate KEV re-fetch (runs in the background)."""
    if run_async is None:
        raise HTTPException(503, "Database not available")
    try:
        # blocking fetch with a generous timeout so the caller gets the fresh count
        count = run_async(cve_service.fetch_and_store(), timeout=45)
        return {"status": "refreshed", "entries": count}
    except Exception as exc:
        raise HTTPException(502, f"CVE refresh failed: {exc}")


@router.get("/{cve_id}")
def cve_detail(cve_id: str, _: dict = Depends(require_analyst)):
    if run_async is None:
        raise HTTPException(404, "CVE not found")
    try:
        from backend.app.core.database import get_cve
        entry = run_async(get_cve(cve_id), timeout=10)
    except Exception:
        raise HTTPException(404, "CVE not found")
    if entry is None:
        raise HTTPException(404, "CVE not found")
    return entry
