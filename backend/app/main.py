# backend/app/main.py
# Main entry point for the Network Attack Simulator backend API.
# Initializes FastAPI and wires all functional routers.

from fastapi import FastAPI

from backend.app.api.routes_attack import router as attack_router
from backend.app.api.routes_metrics import router as metrics_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.api.routes_response import router as response_router
from backend.app.api.routes_audit import router as audit_router



# Initialize the FastAPI application
app = FastAPI(title="Network Attack Simulator API")


# Include API routers
app.include_router(attack_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(response_router)
app.include_router(audit_router)


@app.get("/api/health")
def health():
    """
    Health check endpoint.

    Returns:
        dict: Service health status.
    """
    return {"status": "ok"}