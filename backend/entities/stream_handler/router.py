from fastapi import APIRouter, HTTPException
from .services import main_stream_handler 

router = APIRouter()

# API endpoint to start the video stream handler.
@router.post("/start", status_code=200)
async def start_handler():
    success = main_stream_handler.start() 
    if not success:
        raise HTTPException(status_code=400, detail="Handler is already running.")
    return {"status": "success", "message": "Stream handler started."}

# API endpoint to stop the video stream handler.
@router.post("/stop", status_code=200)
async def stop_handler():
    success = main_stream_handler.stop()
    if not success:
        raise HTTPException(status_code=400, detail="Handler is not running or failed to stop.")
    return {"status": "success", "message": "Stream handler stopped."}