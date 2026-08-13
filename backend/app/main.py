import asyncio
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
from backend.app.services.auto_attack import auto_attack_loop
from backend.app.services.demo_mode import DEMO_MODE, enable as demo_enable, disable as demo_disable

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    aa_task = asyncio.create_task(auto_attack_loop())
    if DEMO_MODE:
        await demo_enable()   # honours env var on boot; runtime toggle takes over after
    yield
    aa_task.cancel()
    try:
        await aa_task
    except asyncio.CancelledError:
        pass
    await demo_disable()      # clean shutdown regardless of runtime state


app = FastAPI(title="Network Attack Simulator API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
