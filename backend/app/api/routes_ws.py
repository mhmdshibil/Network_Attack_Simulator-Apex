"""WebSocket endpoint — Phase 8."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.services.ws_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/detections")
async def ws_detections(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Keep the connection alive; server pushes events via broadcast
            await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
