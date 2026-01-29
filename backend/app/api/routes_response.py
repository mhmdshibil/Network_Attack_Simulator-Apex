from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.response.engine import evaluate_and_respond

router = APIRouter(
    prefix="/api/respond",
    tags=["Response"]
)


class RespondRequest(BaseModel):
    ip: str
    window: str = "5m"


@router.post("/")
def respond(request: RespondRequest):
    try:
        result = evaluate_and_respond(
            ip=request.ip,
            window=request.window
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))