from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from schema import Token, RefreshToken, AccessTokenRepsonse

router = APIRouter(
    prefix='/auth', 
    tags=['Auth']
)

@router.post("/token", response_model=Token)
def login(form_data: )