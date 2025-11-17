from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from . import services
from entities.common.models.model_user import User
from core.dependencies import get_current_user
from .websocket_manager import manager

router = APIRouter(prefix="/stream", tags=["Stream"])

# API endpoint to start the video stream handler.
@router.post("/{stream_id}/start", status_code=200)
async def start_handler(stream_id: str, user: User = Depends(get_current_user)):
    success = services.start_stream_processing(stream_id=stream_id, admin_id=user.id) 
    if not success:
        raise HTTPException(status_code=400, detail=f"Handler for stream '{stream_id}' is already running.")
    return {"status": "success", "message": f"Stream handler for '{stream_id}' started."}

# API endpoint to stop the video stream handler.
@router.post("/{stream_id}/stop", status_code=200)
async def stop_handler(stream_id: str, user: User = Depends(get_current_user)):
    success = services.stop_stream_processing(stream_id=stream_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Handler for stream '{stream_id}' is not running or failed to stop.")
    return {"status": "success", "message": f"Stream handler for '{stream_id}' stopped."}

# WebSocket endpoint for streaming frames to frontend
@router.websocket("/{stream_id}/ws")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    """
    WebSocket endpoint for receiving processed frames from a specific stream.
    Clients connect to this endpoint to receive real-time frame updates.
    Uses binary frames for efficiency and includes heartbeat mechanism.
    """
    await manager.connect(websocket, stream_id)
    try:
        # Keep the connection alive and listen for client messages
        while True:
            # Wait for any message from client (heartbeat or control messages)
            data = await websocket.receive_text()
            
            try:
                import json
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    # Respond to ping to confirm connection is alive
                    await websocket.send_json({"type": "pong", "timestamp": message.get("timestamp")})
                elif message.get("type") == "pong":
                    # Client acknowledged our ping
                    pass
                    
            except json.JSONDecodeError:
                # Legacy support for simple text messages
                if data == "ping":
                    await websocket.send_text("pong")
                    
    except WebSocketDisconnect:
        await manager.disconnect(websocket, stream_id)
    except Exception as e:
        print(f"WebSocket error for stream {stream_id}: {e}")
        await manager.disconnect(websocket, stream_id)