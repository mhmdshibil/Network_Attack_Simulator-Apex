"""
WebSocket connection manager — Phase 8.

Global singleton so detection_service.py can broadcast without
importing the router (avoids circular imports).
"""
import asyncio
import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            self._connections = [c for c in self._connections if c is not ws]

    async def broadcast(self, data: dict):
        payload = json.dumps(data)
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                self._connections = [c for c in self._connections if c not in dead]

    def broadcast_sync(self, data: dict):
        """Fire-and-forget broadcast from synchronous code (detection loop)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.broadcast(data))
        except RuntimeError:
            pass   # no event loop — running outside server context


manager = ConnectionManager()
