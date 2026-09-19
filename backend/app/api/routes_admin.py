"""Admin endpoints — Phase 4A (Demo Polish)."""
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header

from backend.app.core.auth import require_admin
from backend.app.core.paths import (
    DETECTIONS_FILE, AUDIT_EVENTS_FILE, DECISION_AUDIT_FILE,
    REPUTATION_FILE, HARD_BLOCKED_IPS_FILE,
)
from backend.app.services.ws_manager import manager as ws_manager

router = APIRouter(prefix="/api/admin", tags=["admin"])

_ENFORCE_MODE = os.getenv("ENFORCE_MODE", "dry").lower()

_DETECTION_HEADER = "ip,timestamp,label,action,risk_score\n"
_AUDIT_CSV_HEADER = "timestamp,ip,decision,severity,risk_score,confidence,reason\n"


@router.post("/reset-demo")
async def reset_demo(
    x_confirm_reset: Optional[str] = Header(default=None),
    _: dict = Depends(require_admin),
):
    """
    Clear all demo data for a clean presentation slate.
    Only available in dry enforcement mode (ENFORCE_MODE=dry).
    Requires X-Confirm-Reset: yes header.
    """
    if _ENFORCE_MODE == "live":
        raise HTTPException(
            status_code=403,
            detail="Reset not allowed in live enforcement mode",
        )
    if x_confirm_reset != "yes":
        raise HTTPException(
            status_code=400,
            detail="Send X-Confirm-Reset: yes header",
        )

    cleared: list[str] = []

    # 1 — detections.csv
    try:
        DETECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        DETECTIONS_FILE.write_text(_DETECTION_HEADER)
        cleared.append("detections.csv")
    except Exception as e:
        print(f"[RESET] detections.csv: {e}")

    # 2 — security_events.jsonl
    try:
        AUDIT_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_EVENTS_FILE.write_text("")
        cleared.append("security_events.jsonl")
    except Exception as e:
        print(f"[RESET] security_events.jsonl: {e}")

    # 3 — decision_audit.csv
    try:
        DECISION_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        DECISION_AUDIT_FILE.write_text(_AUDIT_CSV_HEADER)
        cleared.append("decision_audit.csv")
    except Exception as e:
        print(f"[RESET] decision_audit.csv: {e}")

    # 4 — ip_reputation.json
    try:
        REPUTATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPUTATION_FILE.write_text("{}")
        cleared.append("ip_reputation.json")
    except Exception as e:
        print(f"[RESET] ip_reputation.json: {e}")

    # 5 — hard_blocked_ips.json
    try:
        HARD_BLOCKED_IPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        HARD_BLOCKED_IPS_FILE.write_text("{}")
        cleared.append("hard_blocked_ips.json")
    except Exception as e:
        print(f"[RESET] hard_blocked_ips.json: {e}")

    # 6 — database tables (best-effort)
    try:
        from backend.app.core import database as db
        from sqlalchemy import text as sql_text
        engine, _ = db._init_engine()
        async with engine.begin() as conn:
            for tbl in ("detections", "triage_cases", "audit_events"):
                try:
                    await conn.execute(sql_text(f"DELETE FROM {tbl}"))  # noqa: S608
                except Exception:
                    pass
        cleared.append("database tables")
    except Exception as e:
        print(f"[RESET] DB truncate (non-critical): {e}")

    # 7 — broadcast reset event
    await ws_manager.broadcast({"type": "demo_reset", "message": "System reset for demo"})

    return {
        "status": "reset",
        "cleared": cleared,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
