"""WebSocket connection manager for /ws/live-updates.

Tracks all connected clients and broadcasts typed LiveUpdateEvent messages
the moment a scheduler cycle completes. This is the real-time backbone:
frontend charts/KPIs/tables update without a page refresh.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[WebSocket, str] = {}  # ws -> session tag
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, tag: str = "client") -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections[websocket] = tag
        logger.info("WS client connected (total=%d)", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections.pop(websocket, None)
        logger.info("WS client disconnected (total=%d)", len(self.active_connections))

    @property
    def client_count(self) -> int:
        return len(self.active_connections)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        """Send a typed event to every connected client."""
        message = {
            "type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        dead: List[WebSocket] = []
        for websocket in list(self.active_connections.keys()):
            try:
                await websocket.send_json(message)
            except Exception as exc:
                logger.warning("broadcast send failed (%s); dropping socket", exc)
                dead.append(websocket)
        for ws in dead:
            await self.disconnect(ws)

    async def send_hello(self, websocket: WebSocket) -> None:
        await websocket.send_json(
            {
                "type": "hello",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "message": "Connected to BazaarPulse live feed",
                    "client_count": self.client_count,
                },
            }
        )


# Singleton shared across the app.
manager = ConnectionManager()
