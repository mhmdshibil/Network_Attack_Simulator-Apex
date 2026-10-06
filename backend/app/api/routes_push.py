"""
Push Notification API — Phase 6E.

GET    /api/push/vapid-public-key   — public VAPID key (no auth)
POST   /api/push/subscribe          — register a push subscription (analyst+)
DELETE /api/push/subscribe          — remove a push subscription (analyst+)
"""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_analyst
from backend.app.core.database import run_async
from sqlalchemy import select as sa_select

router = APIRouter(prefix="/api/push", tags=["push"])

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()


@router.get("/vapid-public-key")
def vapid_public_key():
    """Public endpoint — safe to expose."""
    return {"public_key": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
def subscribe(body: dict, _: dict = Depends(require_analyst)):
    endpoint = body.get("endpoint", "").strip()
    keys     = body.get("keys") or {}
    p256dh   = keys.get("p256dh", "")
    auth     = keys.get("auth", "")
    ua       = str(body.get("user_agent", ""))[:200]

    if not endpoint:
        raise HTTPException(422, "endpoint is required")

    async def _upsert():
        from backend.app.models.push_model import PushSubscription
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(
                sa_select(PushSubscription).where(PushSubscription.endpoint == endpoint)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.p256dh     = p256dh
                existing.auth       = auth
                existing.user_agent = ua
                existing.last_used  = datetime.now(timezone.utc)
                await s.commit()
                return {"id": existing.id, "status": "updated"}
            else:
                sub = PushSubscription(
                    id=str(uuid.uuid4()),
                    endpoint=endpoint, p256dh=p256dh, auth=auth, user_agent=ua,
                )
                s.add(sub)
                await s.commit()
                return {"id": sub.id, "status": "subscribed"}

    try:
        return run_async(_upsert(), timeout=10)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.delete("/subscribe")
def unsubscribe(body: dict, _: dict = Depends(require_analyst)):
    endpoint = body.get("endpoint", "").strip()
    if not endpoint:
        raise HTTPException(422, "endpoint is required")

    async def _delete():
        from backend.app.models.push_model import PushSubscription
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(
                sa_select(PushSubscription).where(PushSubscription.endpoint == endpoint)
            )
            sub = result.scalar_one_or_none()
            if sub:
                await s.delete(sub)
                await s.commit()
                return {"unsubscribed": True}
            return {"unsubscribed": False}

    try:
        return run_async(_delete(), timeout=10)
    except Exception as exc:
        raise HTTPException(500, str(exc))
