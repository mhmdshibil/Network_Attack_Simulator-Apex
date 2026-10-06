"""
Webhook API — Phase 6C.

GET    /api/webhooks              — list (admin)
POST   /api/webhooks              — create (admin)
PUT    /api/webhooks/{id}         — update (admin)
DELETE /api/webhooks/{id}         — delete (admin)
POST   /api/webhooks/{id}/test    — send test payload (admin)
GET    /api/webhooks/{id}/deliveries — last 50 deliveries (admin)
POST   /api/webhooks/{id}/toggle  — enable/disable (admin)

/test, /deliveries, /toggle declared BEFORE /{id} capture paths.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_admin
from backend.app.core.database import run_async

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

try:
    from backend.app.services.webhook_service import webhook_service as _svc
except Exception as _e:
    _svc = None  # type: ignore[assignment]
    print(f"[WEBHOOKS] service unavailable: {_e}")

_VALID_EVENTS = {"detection", "campaign", "baseline_alert", "triage_resolved"}

_TEST_PAYLOAD = {
    "type": "detection",
    "ip": "203.0.113.99",
    "label": "bruteforce",
    "confidence": 0.92,
    "risk_score": 88,
    "action": "blocked",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "test": True,
}


def _svc_or_503():
    if _svc is None:
        raise HTTPException(503, "Webhook service unavailable")
    return _svc


@router.get("")
def list_webhooks(_: dict = Depends(require_admin)):
    return run_async(_svc_or_503()._db_list(), timeout=10)


@router.post("")
def create_webhook(body: dict, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    if not body.get("name"):
        raise HTTPException(422, "name is required")
    url = body.get("url", "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(422, "url must start with http:// or https://")
    events = body.get("events", [])
    invalid = set(events) - _VALID_EVENTS
    if invalid:
        raise HTTPException(422, f"Unknown event types: {invalid}. Valid: {_VALID_EVENTS}")
    try:
        return run_async(svc._db_create(body), timeout=10)
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Sub-paths BEFORE /{id} ────────────────────────────────────────────────────

@router.post("/{wh_id}/test")
def test_webhook(wh_id: str, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    webhooks = run_async(svc._db_list(), timeout=5)
    wh = next((w for w in webhooks if w["id"] == wh_id), None)
    if not wh:
        raise HTTPException(404, "Webhook not found")

    # Deliver synchronously so we can report the result inline
    class _WH:
        id      = wh["id"]
        url     = wh["url"]
        events  = wh.get("events", [])
        secret  = None  # masked in list — secret not returned, test without signing
        enabled = True

    async def _do_test():
        from backend.app.services.webhook_service import _post_once, _TIMEOUT
        import json, time
        body = json.dumps(_TEST_PAYLOAD, default=str).encode()
        hdrs = {
            "Content-Type": "application/json",
            "X-Apex-Event": "detection",
            "X-Apex-Timestamp": str(int(time.time())),
            "User-Agent": "ApexArgus/2.0 test",
        }
        status, code = await _post_once(wh["url"], hdrs, body)
        return {"status": status, "response_code": code}

    try:
        result = run_async(_do_test(), timeout=15)
        return result
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


@router.get("/{wh_id}/deliveries")
def deliveries(wh_id: str, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    return run_async(svc._db_deliveries(wh_id), timeout=10)


@router.post("/{wh_id}/toggle")
def toggle_webhook(wh_id: str, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    webhooks = run_async(svc._db_list(), timeout=5)
    wh = next((w for w in webhooks if w["id"] == wh_id), None)
    if not wh:
        raise HTTPException(404, "Webhook not found")
    result = run_async(svc._db_update(wh_id, {"enabled": not wh["enabled"]}), timeout=10)
    return result


@router.put("/{wh_id}")
def update_webhook(wh_id: str, body: dict, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    if "url" in body:
        url = body["url"].strip()
        if not url.startswith(("http://", "https://")):
            raise HTTPException(422, "url must start with http:// or https://")
    if "events" in body:
        invalid = set(body["events"]) - _VALID_EVENTS
        if invalid:
            raise HTTPException(422, f"Unknown event types: {invalid}")
    result = run_async(svc._db_update(wh_id, body), timeout=10)
    if not result:
        raise HTTPException(404, "Webhook not found")
    return result


@router.delete("/{wh_id}")
def delete_webhook(wh_id: str, _: dict = Depends(require_admin)):
    svc = _svc_or_503()
    if not run_async(svc._db_delete(wh_id), timeout=10):
        raise HTTPException(404, "Webhook not found")
    return {"deleted": True}
