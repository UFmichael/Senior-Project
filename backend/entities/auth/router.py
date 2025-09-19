from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from schema import Token, RefreshToken, AccessTokenRepsonse
from core.config import get_settings
from core.security import authenticate_user 

router = APIRouter(
    prefix='/auth', 
    tags=['Auth']
)

@router.post("/token", response_model=Token)
def login(form_data: )