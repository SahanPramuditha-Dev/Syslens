import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("syslens.socket")

class ConnectionManager:
    """Manages WebSocket clients streaming system telemetry data."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept connection and add to registry."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove connection from registry."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send message directly to a client."""
        await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        """Broadcast telemetry updates to all connected dashboard client sessions."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.add(connection)
                
        # Clean up dead connections
        for conn in disconnected:
            self.disconnect(conn)
            
manager = ConnectionManager()
