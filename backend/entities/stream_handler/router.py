from fastapi import APIRouter, HTTPException, Depends
from . import services
from entities.common.models.model_user import User
from core.dependencies import get_current_user

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