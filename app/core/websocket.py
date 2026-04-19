"""
WebSocket connection manager for real-time attendance updates.
Clients subscribe to a session_id and receive notifications when attendance changes.
"""
from fastapi import WebSocket
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)


class AttendanceWSManager:
    def __init__(self):
        # session_id -> set of connected WebSockets
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)
        logger.debug("WS connected", extra={"type": "ws_connect", "session_id": session_id})

    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]

    async def broadcast(self, session_id: int, data: dict):
        """Send a message to all clients watching a session."""
        if session_id not in self._connections:
            return
        dead = []
        for ws in self._connections[session_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[session_id].discard(ws)


# Singleton
attendance_ws = AttendanceWSManager()
