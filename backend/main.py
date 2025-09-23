from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from core.middleware import ProcessTimeMiddleware
from core.config import get_settings
from api import register_routes

def create_app() -> FastAPI:

    settings = get_settings() 


    app = FastAPI(title="Threat Neutralizer")

    # Timimng middlewear
    app.add_middleware(ProcessTimeMiddleware)


    app.add_middleware(
        CORSMiddleware, 
        allow_origins = settings.ALLOWED_ORIGINS,
        allow_credentials = True, 
        allow_methods = ["*"],
        allow_headers = ["Authorization", "Content-Type"]
    )

    register_routes(app)

    @app.get("/", include_in_schema=False)
    def read_root():
        return Response("Server is running")

    return app

app = create_app()
    
        