from fastapi import FastAPI
from backend.app.api.routes_attack import router as attack_router
from backend.app.api.routes_metrics import router as metrics_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.api.routes_response import router as response_router

app = FastAPI(title="Network Attack Simulator API")

app.include_router(attack_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(response_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}