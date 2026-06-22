import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes_attack import router as attack_router
from backend.app.api.routes_metrics import router as metrics_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.api.routes_response import router as response_router
from backend.app.api.routes_audit import router as audit_router
from backend.app.api.routes_system import router as system_router
from backend.app.api.routes_alerts import router as alerts_router
from backend.app.api.routes_auto_attack import router as auto_attack_router
from backend.app.services.auto_attack import auto_attack_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(auto_attack_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Network Attack Simulator API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(attack_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(response_router)
app.include_router(audit_router)
app.include_router(system_router)
app.include_router(alerts_router)
app.include_router(auto_attack_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
