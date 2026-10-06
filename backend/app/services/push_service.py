"""
PushService — Phase 6E: Web Push / VAPID notifications.

Sends browser push notifications to all subscribed clients via pywebpush.
Called from notification_service when a Slack/email alert fires.

VAPID keys must be set in .env:
  VAPID_PUBLIC_KEY=...
  VAPID_PRIVATE_KEY=...
  VAPID_EMAIL=admin@apex-argus.io

Without keys the service is silently disabled.
"""
import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select as sa_select

VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY",  "").strip()
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").strip()
VAPID_EMAIL       = os.getenv("VAPID_EMAIL",       "admin@apex-argus.io").strip()

_ENABLED = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)

try:
    from pywebpush import webpush, WebPushException
    _WEBPUSH = True
except ImportError:
    _WEBPUSH = False


async def _load_subscriptions() -> list:
    try:
        from backend.app.models.push_model import PushSubscription
        from backend.app.core.database import _init_engine
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(PushSubscription))
            return result.scalars().all()
    except Exception as e:
        print(f"[PUSH] load subscriptions failed: {e}")
        return []


async def _remove_subscription(endpoint: str) -> None:
    try:
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
    except Exception:
        pass


class PushService:
    async def send_to_all(self, title: str, body: str, url: str = "/", tag: str = "apex-alert") -> None:
        if not _ENABLED:
            return
        if not _WEBPUSH:
            print("[PUSH] pywebpush not installed — run: pip install pywebpush")
            return

        subscriptions = await _load_subscriptions()
        if not subscriptions:
            return

        payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh or "", "auth": sub.auth or ""},
                    },
                    data=payload,
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
                )
            except Exception as e:
                err_str = str(e)
                # 410 Gone = subscription expired/unregistered — remove it
                if "410" in err_str or "expired" in err_str.lower():
                    await _remove_subscription(sub.endpoint)
                    print(f"[PUSH] removed expired subscription: {sub.endpoint[:40]}…")
                else:
                    print(f"[PUSH] delivery failed for {sub.endpoint[:40]}…: {e}")


# Module-level singleton
push_service = PushService()
