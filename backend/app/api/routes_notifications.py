"""Notification management API — Phase 3 / Task 3.

Admin-only endpoints to inspect config, send test notifications, and review the
in-memory notification log. All actual alert firing is done by
notification_service.py triggered from the detection pipeline.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.core.auth import require_admin

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

try:
    from backend.app.services.notification_service import service as _notify
except Exception:
    _notify = None  # type: ignore[assignment]


class TestIn(BaseModel):
    channel: str = "all"   # "slack" | "email" | "all"


@router.get("/config")
def get_config(_: dict = Depends(require_admin)):
    """Returns which notification channels are configured and current rate-limit settings."""
    if _notify is None:
        return {
            "slack_configured": False, "email_configured": False,
            "dedup_window_minutes": 5,
            "rate_limits": {"slack_per_minute": 10, "email_per_hour": 20},
        }
    return {
        "slack_configured": _notify.slack_configured,
        "email_configured": _notify.email_configured,
        "dedup_window_minutes": 5,
        "rate_limits": {"slack_per_minute": 10, "email_per_hour": 20},
    }


@router.post("/test")
def test_notifications(body: TestIn, _: dict = Depends(require_admin)):
    """Send a test notification to Slack, email, or both channels."""
    if _notify is None:
        raise HTTPException(503, "Notification service unavailable")

    results = {}
    ch = body.channel.lower()
    if ch in ("slack", "all"):
        results["slack"] = _notify.send_test_slack()
    else:
        results["slack"] = "skipped"
    if ch in ("email", "all"):
        results["email"] = _notify.send_test_email()
    else:
        results["email"] = "skipped"
    return results


@router.get("/log")
def get_log(_: dict = Depends(require_admin)):
    """Returns the last 50 notification events (in-memory, resets on restart)."""
    if _notify is None:
        return []
    return _notify.get_log()
