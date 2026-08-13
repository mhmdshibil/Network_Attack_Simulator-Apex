"""Demo mode endpoints — Phase 16."""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.core.auth import require_analyst
from backend.app.services.demo_mode import (
    ATTACK_CLASSES,
    fire_attack,
    get_status,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])

_VALID = set(ATTACK_CLASSES)


@router.post("/trigger")
async def trigger_demo_attack(
    type: Optional[str] = Query(default=None, description="Attack class, or omit for random"),
    _: dict = Depends(require_analyst),
):
    """
    Immediately fire one attack through the real detection pipeline.
    Does not affect the scheduled rotation — safe to call at any time.
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


@router.get("/status")
def demo_status(_: dict = Depends(require_analyst)):
    """Current demo scheduler state — next fire countdown, last triggered, rotation deck."""
    return get_status()
