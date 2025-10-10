from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import UnidentifiedImageError
from .model import YOLOModel


router = APIRouter(prefix="/yolo", tags=["YOLO Detection"])


model = YOLOModel()

@router.post("/detect")
async def detect_objects(file: UploadFile = File(...)):
    """
    Endpoint to detect objects in uploaded images
    """
    contents = await file.read()

    try:
        results = await model.predict(contents)
        return {"results": results}
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail={"error": "Cannot identify image file"})

@router.post("/load-model")
async def load_model(model_path: str):
    """
    Endpoint to load a specific YOLO model
    """
    model.load_model(model_path)
    return {"message": "Model loaded successfully"}
