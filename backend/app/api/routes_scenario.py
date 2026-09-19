"""Scenario endpoints — Phase 4A (Demo Polish)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.core.auth import require_analyst
from backend.app.services.scenario_service import service, SCENARIOS

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


class ScenarioStartBody(BaseModel):
    name: str = "corporate_breach"


@router.post("/start")
async def start_scenario(
    body: ScenarioStartBody,
    _: dict = Depends(require_analyst),
):
    if body.name not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Unknown scenario '{body.name}'")
    status = service.get_status()
    if status["is_running"]:
        raise HTTPException(status_code=409, detail="A scenario is already running")
    scenario = SCENARIOS[body.name]
    await service.run_scenario(body.name)
    return {
        "status": "started",
        "scenario": body.name,
        "duration_seconds": scenario["duration_seconds"],
        "acts": len(scenario["acts"]),
    }


@router.post("/stop")
def stop_scenario(_: dict = Depends(require_analyst)):
    completed = service.stop_scenario()
    return {"status": "stopped", "completed_acts": completed}


@router.get("/status")
def scenario_status(_: dict = Depends(require_analyst)):
    return service.get_status()
