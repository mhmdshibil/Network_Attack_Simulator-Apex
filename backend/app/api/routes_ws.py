"""WebSocket endpoint — Phase 8 / Phase 11 auth."""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from backend.app.services.ws_manager import manager
from backend.app.core.auth import ws_require_analyst

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/detections")
async def ws_detections(ws: WebSocket, _: dict = Depends(ws_require_analyst)):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
