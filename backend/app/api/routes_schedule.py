"""
Scheduled Scenario Replay — Phase 7 Task 5c.

A tiny cron-driven scheduler that auto-launches the corporate_breach scenario.
State is persisted to data/policies/schedule.json. A background loop in the app
lifespan calls tick() every 60 s; when the current minute matches the cron
expression (and no scenario is running), it fires the scenario.

GET  /api/schedule/status   — analyst
POST /api/schedule/set      — admin   { cron: "0 9 * * 1-5" }
POST /api/schedule/disable  — admin

Inline 5-field cron parser: minute hour day-of-month month day-of-week.
Supports  *  ,  specific values,  ranges (1-5),  and steps (*/2).
Day-of-week uses cron convention: 0 = Sunday … 6 = Saturday.
"""
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.auth import require_admin, require_analyst
from backend.app.core.paths import BASE_DIR

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

_FILE = BASE_DIR / "data" / "policies" / "schedule.json"
_DEFAULT = {"enabled": False, "cron": "0 9 * * 1-5", "last_run": None, "total_runs": 0}


def _load() -> dict:
    if _FILE.exists():
        try:
            return {**_DEFAULT, **json.loads(_FILE.read_text())}
        except Exception:
            pass
    return dict(_DEFAULT)


def _save(data: dict) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(json.dumps(data, indent=2))


# ── Cron parsing ──────────────────────────────────────────────────────────────

def _match_field(field: str, value: int) -> bool:
    for part in field.split(","):
        part = part.strip()
        if part == "*":
            return True
        if part.startswith("*/"):
            try:
                step = int(part[2:])
                if step > 0 and value % step == 0:
                    return True
            except ValueError:
                continue
        elif "-" in part:
            try:
                a, b = part.split("-")
                if int(a) <= value <= int(b):
                    return True
            except ValueError:
                continue
        else:
            try:
                if int(part) == value:
                    return True
            except ValueError:
                continue
    return False


def _cron_dow(dt: datetime) -> int:
    """Python weekday (Mon=0..Sun=6) → cron dow (Sun=0..Sat=6)."""
    return (dt.weekday() + 1) % 7


def cron_matches(cron: str, dt: datetime) -> bool:
    fields = cron.split()
    if len(fields) != 5:
        return False
    minute, hour, dom, month, dow = fields
    return (
        _match_field(minute, dt.minute) and
        _match_field(hour, dt.hour) and
        _match_field(dom, dt.day) and
        _match_field(month, dt.month) and
        _match_field(dow, _cron_dow(dt))
    )


def _next_run(cron: str, after: datetime) -> str | None:
    """Scan forward minute-by-minute (up to 14 days) for the next match."""
    if len(cron.split()) != 5:
        return None
    cursor = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(14 * 24 * 60):
        if cron_matches(cron, cursor):
            return cursor.isoformat()
        cursor += timedelta(minutes=1)
    return None


def _human(cron: str) -> str:
    """Best-effort human-readable summary of common cron shapes."""
    fields = cron.split()
    if len(fields) != 5:
        return "invalid cron expression"
    minute, hour, dom, month, dow = fields
    dow_names = {"1-5": "weekdays", "0,6": "weekends", "*": "every day"}
    when_day = dow_names.get(dow, f"dow={dow}")
    if minute.isdigit() and hour.isdigit():
        return f"at {int(hour):02d}:{int(minute):02d} on {when_day}"
    return f"min={minute} hour={hour} {when_day}"


# ── Background tick (called every 60 s from the app lifespan) ──────────────────

async def tick() -> None:
    """Fire the scenario if the current minute matches and nothing is running."""
    cfg = _load()
    if not cfg.get("enabled"):
        return
    now = datetime.now()
    now_min = now.replace(second=0, microsecond=0).isoformat()
    if not cron_matches(cfg["cron"], now):
        return
    # Avoid double-firing within the same minute.
    if cfg.get("last_run") == now_min:
        return
    try:
        from backend.app.services.scenario_service import service as scenario
        if scenario.get_status().get("is_running"):
            return
        await scenario.run_scenario("corporate_breach")
        cfg["last_run"] = now_min
        cfg["total_runs"] = int(cfg.get("total_runs", 0)) + 1
        _save(cfg)
        print(f"[SCHEDULE] fired corporate_breach at {now_min}")
    except Exception as exc:  # pragma: no cover
        print(f"[SCHEDULE] fire failed: {exc}")


async def schedule_loop() -> None:
    import asyncio
    print("[SCHEDULE] loop started")
    while True:
        try:
            await tick()
        except Exception as exc:  # pragma: no cover
            print(f"[SCHEDULE] tick error: {exc}")
        await asyncio.sleep(60)


# ── Endpoints ─────────────────────────────────────────────────────────────────

def _status_payload() -> dict:
    cfg = _load()
    return {
        **cfg,
        "human": _human(cfg["cron"]),
        "next_run": _next_run(cfg["cron"], datetime.now()) if cfg.get("enabled") else None,
    }


@router.get("/status")
def status(_: dict = Depends(require_analyst)):
    return _status_payload()


@router.post("/set")
def set_schedule(body: dict, _: dict = Depends(require_admin)):
    cron = (body.get("cron") or "").strip()
    if len(cron.split()) != 5:
        raise HTTPException(422, "cron must have exactly 5 fields: min hour dom month dow")
    # Validate each field parses against a representative datetime.
    try:
        cron_matches(cron, datetime.now())
    except Exception:
        raise HTTPException(422, "invalid cron expression")
    cfg = _load()
    cfg["cron"] = cron
    cfg["enabled"] = True
    _save(cfg)
    return _status_payload()


@router.post("/disable")
def disable_schedule(_: dict = Depends(require_admin)):
    cfg = _load()
    cfg["enabled"] = False
    _save(cfg)
    return _status_payload()
