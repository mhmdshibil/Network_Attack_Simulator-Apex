from fastapi import APIRouter, Depends
from backend.app.services import auto_attack
from backend.app.core.auth import require_admin, require_analyst

router = APIRouter(prefix="/api/auto-attack", tags=["auto-attack"])


@router.post("/start")
def start_auto_attack(_: dict = Depends(require_admin)):
    auto_attack.set_enabled(True)
    return {"status": "started", "enabled": True}


@router.post("/stop")
def stop_auto_attack(_: dict = Depends(require_admin)):
    auto_attack.set_enabled(False)
    return {"status": "stopped", "enabled": False}


@router.get("/status")
def get_auto_attack_status(_: dict = Depends(require_analyst)):
    return {"enabled": auto_attack.is_enabled()}
