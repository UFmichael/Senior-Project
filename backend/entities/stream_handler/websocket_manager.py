"""
WebSocket manager for streaming processed frames to frontend clients
"""
from fastapi import WebSocket
from typing import Dict, Set, Optional, Deque
import asyncio
import json
import time
from collections import deque, defaultdict

class ConnectionManager:
    def __init__(self):
        # Dictionary mapping stream_id to set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        
        # Frame queue management
        self._frame_queues: Dict[WebSocket, Deque] = {}
        self._max_queue_size = 3  # Drop old frames if queue exceeds this
        
        self._send_times: Dict[WebSocket, float] = {}
        self._slow_connection_threshold = 0.2  # Increased from 0.1 to 0.2 (200ms tolerance)
        
        # Connection health tracking
        self._last_ping_time: Dict[WebSocket, float] = {}
        self._ping_interval = 30  # seconds
        
        # Per-stream frame rate adaptation
        self._stream_frame_stats: Dict[str, Dict] = defaultdict(lambda: {
            'frames_sent': 0,
            'frames_dropped': 0,
            'slow_clients': 0,
            'last_stats_time': time.time()
        })

    async def connect(self, websocket: WebSocket, stream_id: str):
        """Accept a new WebSocket connection for a specific stream"""
        await websocket.accept()
        async with self._lock:
            if stream_id not in self.active_connections:
                self.active_connections[stream_id] = set()
            self.active_connections[stream_id].add(websocket)
            
            # Initialize connection tracking
            self._frame_queues[websocket] = deque(maxlen=self._max_queue_size)
            self._send_times[websocket] = 0
            self._last_ping_time[websocket] = time.time()
            
        print(f"Client connected to stream {stream_id}. Total connections: {len(self.active_connections[stream_id])}")

    async def disconnect(self, websocket: WebSocket, stream_id: str):
        """Remove a WebSocket connection"""
        async with self._lock:
            if stream_id in self.active_connections:
                self.active_connections[stream_id].discard(websocket)
                if not self.active_connections[stream_id]:
                    del self.active_connections[stream_id]
            
            # Clean up connection tracking
            if websocket in self._frame_queues:
                del self._frame_queues[websocket]
            if websocket in self._send_times:
                del self._send_times[websocket]
            if websocket in self._last_ping_time:
                del self._last_ping_time[websocket]
                
        print(f"Client disconnected from stream {stream_id}")

    async def send_frame(self, stream_id: str, frame_data: bytes, detections: list = None):
        """
        Send a frame to all connected clients for a specific stream using binary WebSocket frames.
        Uses a hybrid approach: binary frame data + JSON metadata in separate messages.
        """
        if stream_id not in self.active_connections:
            return

        # Prepare detection metadata as JSON
        metadata = {
            "type": "metadata",
            "stream_id": stream_id,
            "detections": detections or [],
            "timestamp": time.time()
        }
        metadata_json = json.dumps(metadata)

        stats = self._stream_frame_stats[stream_id]
        disconnected = set()
        frames_sent = 0
        frames_dropped = 0
        slow_clients = 0

        for connection in list(self.active_connections[stream_id]):
            try:
                # Check if connection has too many queued frames (backpressure)
                queue = self._frame_queues.get(connection)
                if queue and len(queue) >= self._max_queue_size:
                    frames_dropped += 1
                    # Drop oldest frame from queue
                    if len(queue) > 0:
                        queue.popleft()
                    print(f"[WebSocket] Dropped frame for slow client on stream {stream_id}")
                
                # Measure send time for backpressure detection
                send_start = time.time()
                
                # Send metadata first (small JSON message)
                await connection.send_text(metadata_json)
                
                # Then send binary frame data (efficient!)
                await connection.send_bytes(frame_data)
                
                send_duration = time.time() - send_start
                self._send_times[connection] = send_duration
                
                # Track slow connections
                if send_duration > self._slow_connection_threshold:
                    slow_clients += 1
                
                frames_sent += 1
                
            except Exception as e:
                print(f"Error sending frame to client: {e}")
                disconnected.add(connection)

        # Update statistics
        stats['frames_sent'] += frames_sent
        stats['frames_dropped'] += frames_dropped
        stats['slow_clients'] = slow_clients
        
        # Print stats every 5 seconds
        if time.time() - stats['last_stats_time'] > 5:
            print(f"[WebSocket] Stream {stream_id} stats: "
                  f"sent={stats['frames_sent']}, dropped={stats['frames_dropped']}, "
                  f"slow_clients={slow_clients}/{len(self.active_connections[stream_id])}")
            stats['frames_sent'] = 0
            stats['frames_dropped'] = 0
            stats['last_stats_time'] = time.time()

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[stream_id] -= disconnected
                for conn in disconnected:
                    if conn in self._frame_queues:
                        del self._frame_queues[conn]
                    if conn in self._send_times:
                        del self._send_times[conn]
                    if conn in self._last_ping_time:
                        del self._last_ping_time[conn]

    async def send_ping(self, stream_id: str):
        """Send ping to all connections for a stream to keep them alive"""
        if stream_id not in self.active_connections:
            return
            
        current_time = time.time()
        disconnected = set()
        
        for connection in list(self.active_connections[stream_id]):
            last_ping = self._last_ping_time.get(connection, 0)
            
            # Only ping if enough time has passed
            if current_time - last_ping >= self._ping_interval:
                try:
                    await connection.send_json({"type": "ping", "timestamp": current_time})
                    self._last_ping_time[connection] = current_time
                except Exception as e:
                    print(f"Error sending ping: {e}")
                    disconnected.add(connection)
        
        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[stream_id] -= disconnected
                for conn in disconnected:
                    if conn in self._frame_queues:
                        del self._frame_queues[conn]
                    if conn in self._send_times:
                        del self._send_times[conn]
                    if conn in self._last_ping_time:
                        del self._last_ping_time[conn]

    def has_connections(self, stream_id: str) -> bool:
        """Check if there are any active connections for a stream"""
        return stream_id in self.active_connections and len(self.active_connections[stream_id]) > 0
    
    def get_connection_count(self, stream_id: str) -> int:
        """Get number of active connections for a stream"""
        if stream_id not in self.active_connections:
            return 0
        return len(self.active_connections[stream_id])
    
    def get_slow_client_ratio(self, stream_id: str) -> float:
        """Get ratio of slow clients for adaptive frame rate"""
        if stream_id not in self.active_connections:
            return 0.0
        
        total = len(self.active_connections[stream_id])
        if total == 0:
            return 0.0
            
        slow_count = sum(
            1 for conn in self.active_connections[stream_id]
            if self._send_times.get(conn, 0) > self._slow_connection_threshold
        )
        
        return slow_count / total

# Global instance
manager = ConnectionManager()