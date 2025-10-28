from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from . import services
from entities.common.models.model_user import User
from core.dependencies import get_current_user
import asyncio

router = APIRouter(prefix="/stream", tags=["Stream"])

# API endpoint to start the video stream handler.
@router.post("/{stream_id}/start", status_code=200)
async def start_handler(stream_id: str, user: User = Depends(get_current_user)):
    success = services.start_stream_processing(stream_id=stream_id) 
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

# API endpoint to get the video frames to frontend
@router.get("/{stream_id}/feed")
async def stream_feed(stream_id: str, user: User = Depends(get_current_user)):
    # Streams video frames as Motion JPEG (MJPEG) format.
    handler = services.get_stream_handler(stream_id)
    if not handler or not handler.is_running():
        raise HTTPException(status_code=404, detail=f"Stream '{stream_id}' is not active.")
    
    async def generate_frames():
        try:
            while True:
                frame_data = await handler.get_latest_frame()
                if frame_data is None:
                    await asyncio.sleep(0.033)  # Around 30 FPS
                    continue
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                
                await asyncio.sleep(0.033)  # Around 30 FPS
        except Exception as e:
            print(f"Error streaming frames for {stream_id}: {e}")
    
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
