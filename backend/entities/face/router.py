from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import UnidentifiedImageError
from .services import FaceModel

router = APIRouter(prefix="/face", tags=["Face Detection"])

model = FaceModel()

@router.post("/detect")
async def detect_face(file: UploadFile = File(...)):
    contents = await file.read()

    try:
        results = await model.predict(contents)
        return {"results": results}
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail={"error": "Cannot identify image file"})
