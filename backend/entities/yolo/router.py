from fastapi import APIRouter, UploadFile, File, Depends
from .model import YOLOModel
from entities.common.models.model_user import User
from core.dependencies import get_current_user


router = APIRouter(prefix="/yolo", tags=["YOLO Detection"])

# Initialize YOLO model
model = YOLOModel()

@router.post("/detect")
async def detect_objects(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """
    Endpoint to detect objects in uploaded images
    """
    # Read image file
    contents = await file.read()
    
    # Process image and get predictions
    results = await model.predict(contents)
    
    return {"results": results}

@router.post("/load-model")
async def load_model(model_path: str, user: User = Depends(get_current_user)):
    """
    Endpoint to load a specific YOLO model
    """
    model.load_model(model_path)
    return {"message": "Model loaded successfully"}
