# main.py
# This file is the entry point for the Network Attack Simulator API.
# It initializes the FastAPI application and includes all the API routers.

from fastapi import FastAPI
from backend.app.api.routes_attack import router as attack_router
from backend.app.api.routes_metrics import router as metrics_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.api.routes_response import router as response_router

# Initialize the FastAPI application with a title.
app = FastAPI(title="Network Attack Simulator API")

# Include the API routers for different functionalities.
# Each router handles a specific part of the API.
app.include_router(attack_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(response_router)


@app.get("/api/health")
def health():
    """
    Health check endpoint.
    Returns the status of the API.
    """
    return {"status": "ok"}