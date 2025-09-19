from fastapi import FastAPI, APIRouter

from entities.auth.router import router as auth_router

def register_routes(app: FastAPI):  
    main_router = APIRouter(prefix="", tags=["V1"])

    main_router.include_router(auth_router)

    app.include_router(main_router)