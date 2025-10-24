from fastapi import FastAPI, APIRouter

from entities.auth.router import router as auth_router
from entities.yolo.router import router as yolo_router
from entities.user.router import router as user_router
from entities.face.router import router as face_router
from entities.stream_handler.router import router as stream_router

def register_routes(app: FastAPI):  
    main_router = APIRouter()

    main_router.include_router(auth_router)
    main_router.include_router(yolo_router)
    main_router.include_router(user_router)
    main_router.include_router(face_router)
    main_router.include_router(stream_router)

    app.include_router(main_router)