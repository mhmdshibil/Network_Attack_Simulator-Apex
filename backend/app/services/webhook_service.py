"""
WebhookService — Phase 6C: Outbound webhook integrations.

Delivers detection / campaign / baseline_alert / triage_resolved events to
any registered HTTP endpoint. Never blocks the detection pipeline —
fire-and-forget via asyncio.create_task().

Delivery:
- 5 s timeout per attempt
- 1 retry on failure (2 attempts total)
- HMAC-SHA256 signature if secret is set (X-Apex-Signature header)
- Logs every attempt to webhook_deliveries table
"""
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone

try:
    import httpx as _httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

try:
    from backend.app.core.database import _init_engine
    from sqlalchemy import select as sa_select
    _DB = True
except Exception:
    _DB = False


_TIMEOUT = 5.0
_MAX_ATTEMPTS = 2


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def _log_delivery(webhook_id: str, event_type: str, status: str,
                        response_code, attempt: int) -> None:
    if not _DB:
        return
    try:
        from backend.app.models.webhook_model import WebhookDelivery
        _, sm = _init_engine()
        async with sm() as s:
            s.add(WebhookDelivery(
                id=str(uuid.uuid4()),
                webhook_id=webhook_id,
                event_type=event_type,
                status=status,
                response_code=response_code,
                attempt=attempt,
            ))
            await s.commit()
    except Exception as e:
        print(f"[WEBHOOK] delivery log failed: {e}")


async def _update_webhook_stats(webhook_id: str, success: bool) -> None:
    if not _DB:
        return
    try:
        from backend.app.models.webhook_model import Webhook
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Webhook).where(Webhook.id == webhook_id))
            wh = result.scalar_one_or_none()
            if wh:
                wh.total_deliveries = (wh.total_deliveries or 0) + 1
                if not success:
                    wh.failed_deliveries = (wh.failed_deliveries or 0) + 1
                wh.last_triggered = datetime.now(timezone.utc)
                await s.commit()
    except Exception as e:
        print(f"[WEBHOOK] stats update failed: {e}")


async def _post_once(url: str, headers: dict, body: bytes) -> tuple[str, int]:
    """Returns (status_str, http_status_code)."""
    if not _HTTPX:
        return "failed", 0
    try:
        async with _httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(url, content=body, headers=headers)
            return ("success" if r.status_code < 300 else "failed"), r.status_code
    except _httpx.TimeoutException:
        return "timeout", 0
    except Exception:
        return "failed", 0


async def _deliver_to(webhook, event_type: str, payload: dict) -> None:
    body = json.dumps(payload, default=str).encode()
    ts   = str(int(time.time()))
    hdrs = {
        "Content-Type":    "application/json",
        "X-Apex-Event":    event_type,
        "X-Apex-Timestamp": ts,
        "User-Agent":      "ApexArgus/2.0",
    }
    if webhook.secret:
        hdrs["X-Apex-Signature"] = _sign(webhook.secret, body)

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        status, code = await _post_once(webhook.url, hdrs, body)
        await _log_delivery(webhook.id, event_type, status, code or None, attempt)
        if status == "success":
            await _update_webhook_stats(webhook.id, success=True)
            return
        if attempt < _MAX_ATTEMPTS:
            import asyncio
            await asyncio.sleep(1)

    await _update_webhook_stats(webhook.id, success=False)
    print(f"[WEBHOOK] delivery failed after {_MAX_ATTEMPTS} attempts → {webhook.url}")


class WebhookService:
    async def deliver(self, event_type: str, payload: dict) -> None:
        """
        Find all enabled webhooks subscribed to event_type and deliver in parallel.
        Called via asyncio.create_task() — never blocks the detection pipeline.
        """
        if not _DB:
            return
        try:
            from backend.app.models.webhook_model import Webhook
            _, sm = _init_engine()
            async with sm() as s:
                result = await s.execute(
                    sa_select(Webhook).where(Webhook.enabled.is_(True))
                )
                webhooks = result.scalars().all()
        except Exception as e:
            print(f"[WEBHOOK] DB read failed: {e}")
            return

        import asyncio
        tasks = [
            _deliver_to(wh, event_type, payload)
            for wh in webhooks
            if event_type in (wh.events or [])
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── CRUD helpers (sync wrappers via run_async) ────────────────────────

    async def _db_list(self) -> list[dict]:
        from backend.app.models.webhook_model import Webhook
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Webhook).order_by(Webhook.created_at.desc()))
            return [_wh_to_dict(wh) for wh in result.scalars().all()]

    async def _db_create(self, data: dict) -> dict:
        from backend.app.models.webhook_model import Webhook
        _, sm = _init_engine()
        async with sm() as s:
            wh = Webhook(
                id=str(uuid.uuid4()),
                name=data["name"],
                url=data["url"],
                events=data.get("events", []),
                secret=data.get("secret"),
                enabled=data.get("enabled", True),
            )
            s.add(wh)
            await s.commit()
            await s.refresh(wh)
            return _wh_to_dict(wh)

    async def _db_update(self, wh_id: str, data: dict) -> dict | None:
        from backend.app.models.webhook_model import Webhook
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Webhook).where(Webhook.id == wh_id))
            wh = result.scalar_one_or_none()
            if not wh:
                return None
            for f in ("name", "url", "events", "secret", "enabled"):
                if f in data:
                    setattr(wh, f, data[f])
            await s.commit()
            await s.refresh(wh)
            return _wh_to_dict(wh)

    async def _db_delete(self, wh_id: str) -> bool:
        from backend.app.models.webhook_model import Webhook
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(sa_select(Webhook).where(Webhook.id == wh_id))
            wh = result.scalar_one_or_none()
            if not wh:
                return False
            await s.delete(wh)
            await s.commit()
            return True

    async def _db_deliveries(self, wh_id: str, limit: int = 50) -> list[dict]:
        from backend.app.models.webhook_model import WebhookDelivery
        _, sm = _init_engine()
        async with sm() as s:
            result = await s.execute(
                sa_select(WebhookDelivery)
                .where(WebhookDelivery.webhook_id == wh_id)
                .order_by(WebhookDelivery.delivered_at.desc())
                .limit(limit)
            )
            return [_del_to_dict(d) for d in result.scalars().all()]


def _wh_to_dict(wh) -> dict:
    return {
        "id":               wh.id,
        "name":             wh.name,
        "url":              wh.url,
        "events":           wh.events or [],
        "secret":           "***" if wh.secret else None,
        "enabled":          wh.enabled,
        "created_at":       wh.created_at.isoformat() if wh.created_at else None,
        "last_triggered":   wh.last_triggered.isoformat() if wh.last_triggered else None,
        "total_deliveries": wh.total_deliveries or 0,
        "failed_deliveries": wh.failed_deliveries or 0,
    }


def _del_to_dict(d) -> dict:
    return {
        "id":            d.id,
        "webhook_id":    d.webhook_id,
        "event_type":    d.event_type,
        "status":        d.status,
        "response_code": d.response_code,
        "attempt":       d.attempt,
        "delivered_at":  d.delivered_at.isoformat() if d.delivered_at else None,
    }


# Module-level singleton
webhook_service = WebhookService()
