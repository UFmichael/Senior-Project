from fastapi import FastAPI, APIRouter

from entities.auth.router import router as auth_router
from entities.yolo.router import router as yolo_router

def register_routes(app: FastAPI):  
    main_router = APIRouter()

    main_router.include_router(auth_router)
    main_router.include_router(yolo_router)

    app.include_router(main_router)