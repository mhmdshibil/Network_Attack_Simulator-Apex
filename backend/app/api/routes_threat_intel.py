# backend/app/api/routes_threat_intel.py
# Threat-intelligence lookup endpoints (Phase 2 / Task 3).
#
# The service + DB layer are imported lazily inside the handlers so this router
# is import-safe even when httpx / SQLAlchemy are not installed (the app still
# boots; the endpoints then report the degraded state).

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.auth import require_analyst

router = APIRouter(prefix="/api/threat-intel", tags=["threat-intel"])


def _run(coro, timeout: float):
    """Run a TI/DB coroutine on the shared background DB loop."""
    from backend.app.core.database import run_async
    return run_async(coro, timeout=timeout)


# NOTE: /stats must be declared before /{ip} so it isn't captured as an IP.
@router.get("/stats")
def threat_intel_stats(_: dict = Depends(require_analyst)):
    """
    Threat-intel service stats: configuration, IPs checked today, known-bad
    detected, cache hit rate, and estimated API quota remaining.
    """
    try:
        from backend.app.services.threat_intel_service import service
        return _run(service.stats(), timeout=10)
    except Exception as exc:
        return {"configured": False, "error": f"threat-intel unavailable: {exc}"}


@router.get("/{ip}")
def threat_intel_lookup(ip: str, _: dict = Depends(require_analyst)):
    """
    Return the threat-intel result for an IP. Served from the 24h cache when
    fresh; otherwise fetched live (may be slow — indicated by `source`).
    """
    try:
        from backend.app.services.threat_intel_service import service
        result = _run(service.check_ip(ip), timeout=30)
        result["cached"] = result.get("source") == "cache"
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"threat-intel lookup failed: {exc}",
        )
