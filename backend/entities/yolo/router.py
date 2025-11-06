from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import UnidentifiedImageError
from .model import YOLOWeaponModel, YOLOPoseModel


router = APIRouter(prefix="/yolo", tags=["YOLO Detection"])


weapon_model = YOLOWeaponModel()
people_model = YOLOPoseModel()

@router.post("/detect/weapon")
async def detect_objects(file: UploadFile = File(...)):
    """
    Endpoint to detect objects in uploaded images
    """
    contents = await file.read()

    try:
        results = await weapon_model.predict(contents)
        return {"results": results}
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail={"error": "Cannot identify image file"})

@router.post("/detect/person")
async def detect_people(file: UploadFile = File(...)):
    contents = await file.read() 

    try:
        results = await people_model.predict(contents)
        return {"results": results}
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail={"error": "Cannot identify image file"})

@router.post("/load-model")
async def load_model(model_path: str):
    """
    Endpoint to load a specific YOLO model
    """
    weapon_model.load_model(model_path)
    return {"message": "Model loaded successfully"}
