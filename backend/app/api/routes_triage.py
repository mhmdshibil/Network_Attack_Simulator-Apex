"""Alert Triage API — Phase 3 / Task 1.

CRUD lifecycle for triage cases: open → acknowledged → investigating → resolved | false_positive.
/stats is declared BEFORE /{case_id} to prevent FastAPI routing ambiguity.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.core.auth import require_analyst, AUTH_ENABLED

router = APIRouter(prefix="/api/triage", tags=["triage"])

try:
    from backend.app.core import database as _db
    from backend.app.core.database import run_async
except Exception:
    _db = None
    run_async = None  # type: ignore[assignment]

_EMPTY_STATS = {
    "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    "open_count": 0,
    "total_cases": 0,
    "resolved_cases": 0,
    "sla_breach_count": 0,
    "sla_breach_rate": 0.0,
    "avg_resolution_minutes": None,
    "false_positive_count": 0,
    "false_positive_rate": 0.0,
}


class TriagePatchIn(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


# ── MUST be declared before /{case_id} ──────────────────────────────────────
@router.get("/stats")
def triage_stats(_: dict = Depends(require_analyst)):
    """Open cases by severity, SLA breach count, avg resolution time, false positive rate."""
    if _db is None or run_async is None:
        return _EMPTY_STATS
    try:
        return run_async(_db.get_triage_stats(), timeout=10)
    except Exception:
        return _EMPTY_STATS


@router.get("")
def list_cases(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    assigned_to: Optional[str] = None,
    user: dict = Depends(require_analyst),
):
    """Return all triage cases newest-first, with optional filters."""
    if _db is None or run_async is None:
        return []
    username = user.get("username") if assigned_to == "me" else None
    try:
        return run_async(_db.get_triage_cases(
            status=status,
            severity=severity,
            assigned_to_me=(assigned_to == "me"),
            username=username,
        ), timeout=10)
    except Exception:
        return []


@router.get("/{case_id}")
def get_case(case_id: str, _: dict = Depends(require_analyst)):
    """Single triage case with full details including SLA status."""
    if _db is None or run_async is None:
        raise HTTPException(404, "Triage case not found")
    try:
        case = run_async(_db.get_triage_case(case_id), timeout=10)
    except Exception:
        raise HTTPException(404, "Triage case not found")
    if case is None:
        raise HTTPException(404, "Triage case not found")
    return case


@router.patch("/{case_id}")
def update_case(case_id: str, body: TriagePatchIn, user: dict = Depends(require_analyst)):
    """Update status, assigned_to, and/or notes. Resolved_at is set automatically."""
    if body.status == "false_positive" and AUTH_ENABLED and user.get("role") != "admin":
        raise HTTPException(403, "Admin role required to mark false_positive")
    if _db is None or run_async is None:
        raise HTTPException(503, "Database not available")

    updates: dict = {}
    if body.status is not None:
        updates["status"] = body.status
    if body.assigned_to is not None:
        updates["assigned_to"] = body.assigned_to
    if body.notes is not None:
        updates["notes"] = body.notes
    if body.status in ("resolved", "false_positive"):
        updates["resolved_at"] = datetime.now(timezone.utc).isoformat()

    try:
        case = run_async(_db.update_triage_case(case_id, **updates), timeout=10)
    except Exception as exc:
        raise HTTPException(500, f"Update failed: {exc}")
    if case is None:
        raise HTTPException(404, "Triage case not found")
    return case


@router.post("/{case_id}/acknowledge")
def acknowledge_case(case_id: str, user: dict = Depends(require_analyst)):
    """Shortcut: sets status=acknowledged and assigns the current user."""
    if _db is None or run_async is None:
        raise HTTPException(503, "Database not available")
    username = user.get("username", "anonymous")
    try:
        case = run_async(
            _db.update_triage_case(case_id, status="acknowledged", assigned_to=username),
            timeout=10,
        )
    except Exception as exc:
        raise HTTPException(500, f"Acknowledge failed: {exc}")
    if case is None:
        raise HTTPException(404, "Triage case not found")
    return case
