# routes_response.py
# This file defines the API routes for the automated response engine.
# It includes an endpoint for evaluating and responding to a given IP address.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.response.engine import evaluate_and_respond

# Create a new router for the response endpoints.
router = APIRouter(
    prefix="/api/respond",
    tags=["Response"]
)


class RespondRequest(BaseModel):
    """
    Defines the request model for the /respond endpoint.
    """
    ip: str
    window: str = "5m"


@router.post("/")
def respond(request: RespondRequest):
    """
    Evaluate and respond to a given IP address based on recent activity.
    """
    try:
        # Call the evaluate_and_respond function to get the recommended action.
        result = evaluate_and_respond(
            ip=request.ip,
            window=request.window
        )
        # Return the result of the evaluation.
        return result
    except Exception as e:
        # If an error occurs, return a 500 Internal Server Error.
        raise HTTPException(status_code=500, detail=str(e))