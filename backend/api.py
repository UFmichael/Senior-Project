from fastapi import FastAPI, APIRouter

from entities.auth.router import router as auth_router
from entities.stream_handler.router import router as stream_router

def register_routes(app: FastAPI):  
    main_router = APIRouter()

    main_router.include_router(auth_router)

    app.include_router(main_router)
    app.include_router(stream_router, prefix="/stream")