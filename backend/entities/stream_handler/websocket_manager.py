"""
WebSocket manager for streaming processed frames to frontend clients
"""
from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import json
import base64

class ConnectionManager:
    def __init__(self):
        # Dictionary mapping stream_id to set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        # Track if each connection is ready for next frame (backpressure)
        self._connection_ready: Dict[WebSocket, bool] = {}

    async def connect(self, websocket: WebSocket, stream_id: str):
        """Accept a new WebSocket connection for a specific stream"""
        await websocket.accept()
        async with self._lock:
            if stream_id not in self.active_connections:
                self.active_connections[stream_id] = set()
            self.active_connections[stream_id].add(websocket)
            self._connection_ready[websocket] = True
        print(f"Client connected to stream {stream_id}. Total connections: {len(self.active_connections[stream_id])}")

    async def disconnect(self, websocket: WebSocket, stream_id: str):
        """Remove a WebSocket connection"""
        async with self._lock:
            if stream_id in self.active_connections:
                self.active_connections[stream_id].discard(websocket)
                if not self.active_connections[stream_id]:
                    del self.active_connections[stream_id]
            if websocket in self._connection_ready:
                del self._connection_ready[websocket]
        print(f"Client disconnected from stream {stream_id}")

    async def send_frame(self, stream_id: str, frame_data: bytes, detections: list = None):
        """Send a frame to all connected clients for a specific stream"""
        if stream_id not in self.active_connections:
            return

        # Encode frame as base64 and combine with metadata in single JSON message
        # This is much more efficient than sending JSON + binary separately
        frame_base64 = base64.b64encode(frame_data).decode('utf-8')
        
        message = {
            "type": "frame",
            "stream_id": stream_id,
            "frame": frame_base64,
            "detections": detections or []
        }

        print(f"[WebSocket] Sending frame to {len(self.active_connections[stream_id])} client(s) for stream {stream_id}")

        disconnected = set()
        for connection in list(self.active_connections[stream_id]):
            # Skip if connection is not ready (backpressure)
            if not self._connection_ready.get(connection, True):
                continue
                
            try:
                # Mark connection as busy
                self._connection_ready[connection] = False
                
                # Send combined JSON message
                await connection.send_json(message)
                
                # Mark connection as ready again
                self._connection_ready[connection] = True
            except Exception as e:
                print(f"Error sending frame to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[stream_id] -= disconnected
                for conn in disconnected:
                    if conn in self._connection_ready:
                        del self._connection_ready[conn]

    def has_connections(self, stream_id: str) -> bool:
        """Check if there are any active connections for a stream"""
        return stream_id in self.active_connections and len(self.active_connections[stream_id]) > 0

# Global instance
manager = ConnectionManager()