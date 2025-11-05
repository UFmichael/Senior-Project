"""
WebSocket manager for streaming processed frames to frontend clients
"""
from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        # Dictionary mapping stream_id to set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, stream_id: str):
        """Accept a new WebSocket connection for a specific stream"""
        await websocket.accept()
        async with self._lock:
            if stream_id not in self.active_connections:
                self.active_connections[stream_id] = set()
            self.active_connections[stream_id].add(websocket)
        print(f"Client connected to stream {stream_id}. Total connections: {len(self.active_connections[stream_id])}")

    async def disconnect(self, websocket: WebSocket, stream_id: str):
        """Remove a WebSocket connection"""
        async with self._lock:
            if stream_id in self.active_connections:
                self.active_connections[stream_id].discard(websocket)
                if not self.active_connections[stream_id]:
                    del self.active_connections[stream_id]
        print(f"Client disconnected from stream {stream_id}")

    async def send_frame(self, stream_id: str, frame_data: bytes, detections: list = None):
        """Send a frame to all connected clients for a specific stream"""
        if stream_id not in self.active_connections:
            return

        # Prepare the message with frame and detection data
        message = {
            "type": "frame",
            "stream_id": stream_id,
            "detections": detections or []
        }

        disconnected = set()
        for connection in self.active_connections[stream_id]:
            try:
                # Send JSON metadata first
                await connection.send_json(message)
                # Send binary frame data
                await connection.send_bytes(frame_data)
            except Exception as e:
                print(f"Error sending frame to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[stream_id] -= disconnected

    def has_connections(self, stream_id: str) -> bool:
        """Check if there are any active connections for a stream"""
        return stream_id in self.active_connections and len(self.active_connections[stream_id]) > 0

# Global instance
manager = ConnectionManager()