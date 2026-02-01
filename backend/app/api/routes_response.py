# backend/app/api/routes_response.py
# This module defines the API endpoint for the automated response engine. It provides a route that
# allows clients to trigger an evaluation of a specific IP address. The endpoint takes an IP and a
# time window, then uses the `evaluate_and_respond` function from the response engine to determine
# the appropriate action. This modular approach separates the API interface from the underlying
# business logic, making the system more organized and easier to maintain.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.response.engine import evaluate_and_respond

# Create a new router for the response endpoints. This helps in organizing the API and applies a
# consistent prefix and tag for this functional area.
router = APIRouter(
    prefix="/api/respond",
    tags=["Response"]
)


class RespondRequest(BaseModel):
    """
    Defines the data model for an incoming request to the /respond endpoint.
    It specifies the required 'ip' and an optional 'window' for the analysis.
    Pydantic automatically handles validation to ensure the request body conforms to this structure.
    """
    ip: str
    window: str = "5m"


@router.post("/")
def respond(request: RespondRequest):
    """
    Evaluates the threat level of a given IP address and determines the appropriate response.

    This endpoint serves as the primary interface to the automated response engine. It takes an IP
    address and a time window, then triggers a full evaluation process, which includes attack
    correlation, risk scoring, and confidence assessment. Based on the outcome, it returns a
    recommended action, such as 'monitor', 'alert', or 'block'.

    Args:
        request (RespondRequest): The request body containing the 'ip' to evaluate and an
                                  optional 'window'.

    Returns:
        dict: A dictionary containing the results of the evaluation, including the recommended
              decision and the underlying data that informed it.

    Raises:
        HTTPException: Returns a 500 Internal Server Error if any exception occurs during
                       the evaluation process.
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