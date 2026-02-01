# backend/app/main.py
# This file serves as the main entry point for the Network Attack Simulator's backend API.
# It is responsible for initializing the FastAPI application, which provides the framework for all
# API communications. The script imports and includes several modular routers, each corresponding
# to a different functional area of the application: attacks, metrics, analytics, and responses.
# By structuring the application this way, the codebase remains organized and scalable. This file
# also defines a root-level health check endpoint, which is a standard practice for ensuring the
# API is operational.

from fastapi import FastAPI
from backend.app.api.routes_attack import router as attack_router
from backend.app.api.routes_metrics import router as metrics_router
from backend.app.api.routes_analytics import router as analytics_router
from backend.app.api.routes_response import router as response_router

# Initialize the FastAPI application. The title set here will be used in the API's documentation.
app = FastAPI(title="Network Attack Simulator API")

# Include the API routers from other modules into the main application.
# This modular approach allows for better organization and separation of concerns. Each router
# handles a specific set of endpoints related to its functional area.
app.include_router(attack_router)
app.include_router(metrics_router)
app.include_router(analytics_router)
app.include_router(response_router)


@app.get("/api/health")
def health():
    """
    Provides a simple health check endpoint for the API.

    This endpoint is used to verify that the API is running and responsive. It is a standard
    best practice for service monitoring and can be integrated with uptime-checking tools.
    A successful request to this endpoint will return a JSON object indicating an "ok" status.

    Returns:
        dict: A dictionary with a single key "status" and the value "ok".
    """
    return {"status": "ok"}