import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.app.api.routes_attack import router as attack_router
from backend.app.api.routes_metrics import router as metrics_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.api.routes_response import router as response_router
from backend.app.api.routes_audit import router as audit_router
from backend.app.api.routes_system import router as system_router
from backend.app.api.routes_alerts import router as alerts_router
from backend.app.api.routes_auto_attack import router as auto_attack_router
from backend.app.api.routes_explain import router as explain_router
from backend.app.api.routes_ws import router as ws_router
from backend.app.api.routes_incidents import router as incidents_router
from backend.app.api.routes_auth import router as auth_router
from backend.app.api.routes_demo import router as demo_router
from backend.app.api.reports import router as reports_router
from backend.app.api.routes_threat_intel import router as threat_intel_router
from backend.app.api.routes_triage import router as triage_router
from backend.app.api.routes_notifications import router as notifications_router
from backend.app.api.routes_scenario import router as scenario_router
from backend.app.api.routes_admin import router as admin_router
from backend.app.api.routes_geo import router as geo_router
from backend.app.api.routes_campaigns import router as campaigns_router
from backend.app.api.routes_cve import router as cve_router
from backend.app.api.routes_baseline import router as baseline_router
from backend.app.api.routes_rules import router as rules_router
from backend.app.api.routes_2fa import router as twofa_router
from backend.app.api.routes_webhooks import router as webhooks_router
from backend.app.api.routes_nlq import router as nlq_router
from backend.app.api.routes_push import router as push_router
from backend.app.api.routes_schedule import router as schedule_router, schedule_loop
from backend.app.services.auto_attack import auto_attack_loop
from backend.app.services.demo_mode import DEMO_MODE, enable as demo_enable, disable as demo_disable
from backend.app.services.campaign_service import campaign_sweep_loop
from backend.app.services.cve_service import cve_fetch_loop
from backend.app.services.baseline_service import baseline_service, baseline_persist_loop
from backend.app.services.rules_service import rules_service
from backend.app.services.ws_manager import manager as ws_manager
from backend.app.core.paths import RF_MODEL_PATH, ANOMALY_MODEL_PATH

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Capture the main server loop so worker-thread / background-loop code can
    # schedule WebSocket broadcasts onto it (detections + campaign updates).
    ws_manager.bind_loop(asyncio.get_running_loop())

    aa_task = asyncio.create_task(auto_attack_loop())
    sweep_task = asyncio.create_task(campaign_sweep_loop())
    if DEMO_MODE:
        await demo_enable()   # honours env var on boot; runtime toggle takes over after

    # Phase 2 — create DB tables if the DB layer is available (guarded so a
    # missing DB dependency never blocks startup; CSV/JSONL remain the sink).
    try:
        from backend.app.core.database import init_models
        await init_models()
        print("[DB] tables ready")
    except Exception as db_exc:  # pragma: no cover
        print(f"[DB] skipped table init ({db_exc}); using CSV/JSONL only")

    # Phase 5C — start the CISA KEV fetch loop on the background DB loop (so its
    # DB writes stay on the loop that owns the engine). Tables exist by now.
    try:
        from backend.app.core.database import run_async_bg
        run_async_bg(cve_fetch_loop())
    except Exception as cve_exc:  # pragma: no cover
        print(f"[CVE] fetch loop not started ({cve_exc})")

    # Phase 5D — load persisted baseline and start the 5-minute persistence loop.
    baseline_service.load_from_disk()
    baseline_task = asyncio.create_task(baseline_persist_loop())
    rules_service.load_rules()

    # Phase 7 — scheduled scenario replay (cron-driven, checks every 60 s).
    schedule_task = asyncio.create_task(schedule_loop())

    yield
    aa_task.cancel()
    sweep_task.cancel()
    baseline_task.cancel()
    schedule_task.cancel()
    for _t in (aa_task, sweep_task, baseline_task, schedule_task):
        try:
            await _t
        except asyncio.CancelledError:
            pass
    baseline_service.save_to_disk()   # final flush
    await demo_disable()      # clean shutdown regardless of runtime state


app = FastAPI(title="Network Attack Simulator API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(attack_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(response_router)
app.include_router(audit_router)
app.include_router(system_router)
app.include_router(alerts_router)
app.include_router(auto_attack_router)
app.include_router(explain_router)
app.include_router(ws_router)
app.include_router(incidents_router)
app.include_router(demo_router)
app.include_router(reports_router)
app.include_router(threat_intel_router)
app.include_router(triage_router)
app.include_router(notifications_router)
app.include_router(scenario_router)
app.include_router(admin_router)
app.include_router(geo_router)
app.include_router(campaigns_router)
app.include_router(cve_router)
app.include_router(baseline_router)
app.include_router(rules_router)
app.include_router(twofa_router)
app.include_router(webhooks_router)
app.include_router(nlq_router)
app.include_router(push_router)
app.include_router(schedule_router)


@app.get("/api/health")
async def health():
    db_status = "unavailable"
    try:
        from backend.app.core.database import _init_engine
        from sqlalchemy import text
        engine, _ = _init_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unavailable"

    models_loaded = RF_MODEL_PATH.exists() and ANOMALY_MODEL_PATH.exists()
    status = "ok" if db_status == "connected" and models_loaded else "degraded"

    return {
        "status": status,
        "db": db_status,
        "models_loaded": models_loaded,
        "version": "2.0.0",
    }
