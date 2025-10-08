from fastapi import APIRouter, UploadFile, File
from .model import YOLOModel

router = APIRouter(prefix="/yolo", tags=["YOLO Detection"])


model = YOLOModel()

@router.post("/detect")
async def detect_objects(file: UploadFile = File(...)):
    """
    Endpoint to detect objects in uploaded images
    """
    contents = await file.read()

    results = await model.predict(contents)
    
    return {"results": results}

@router.post("/load-model")
async def load_model(model_path: str):
    """
    Endpoint to load a specific YOLO model
    """
    model.load_model(model_path)
    return {"message": "Model loaded successfully"}
