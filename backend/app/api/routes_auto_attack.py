from fastapi import APIRouter
from backend.app.services import auto_attack

router = APIRouter(prefix="/api/auto-attack", tags=["auto-attack"])


@router.post("/start")
def start_auto_attack():
    auto_attack.set_enabled(True)
    return {"status": "started", "enabled": True}


@router.post("/stop")
def stop_auto_attack():
    auto_attack.set_enabled(False)
    return {"status": "stopped", "enabled": False}


@router.get("/status")
def get_auto_attack_status():
    return {"enabled": auto_attack.is_enabled()}
