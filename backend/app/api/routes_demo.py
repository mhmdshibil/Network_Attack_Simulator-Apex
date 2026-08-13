"""Demo mode endpoints — Phase 16."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.auth import require_analyst, require_admin
from backend.app.services.demo_mode import (
    ATTACK_CLASSES,
    fire_attack,
    get_status,
    enable,
    disable,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])

_VALID = set(ATTACK_CLASSES)


# ── Runtime toggle ────────────────────────────────────────────────────────────

@router.post("/enable")
async def demo_enable(_: dict = Depends(require_admin)):
    """Start the demo scheduler immediately. Requires admin role when AUTH_ENABLED=true."""
    await enable()
    return get_status()


@router.post("/disable")
async def demo_disable(_: dict = Depends(require_admin)):
    """Stop the demo scheduler immediately. In-flight attacks still complete."""
    await disable()
    return get_status()


# ── Status (analyst-visible) ──────────────────────────────────────────────────

@router.get("/status")
def demo_status(_: dict = Depends(require_analyst)):
    """
    Scheduler state: enabled, next_fire_in_seconds, last_triggered, rotation deck.
    Readable by analyst and admin roles (or everyone when AUTH_ENABLED=false).
    """
    return get_status()


# ── Manual trigger (analyst-visible, independent of toggle state) ─────────────

@router.post("/trigger")
async def trigger_demo_attack(
    type: Optional[str] = Query(default=None, description="Attack class, or omit for random"),
    _: dict = Depends(require_analyst),
):
    """
    Fire one attack immediately through the real pipeline, independent of the
    scheduler state. Does not advance the scheduled rotation.
    """
    if type and type not in _VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown attack class '{type}'. Valid: {sorted(_VALID)}",
        )
    try:
        result = await asyncio.to_thread(fire_attack, type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result
