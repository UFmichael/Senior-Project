from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from core.config import get_settings
from core.security import authenticate_user 
from sqlalchemy.orm import Session
from core.dependencies import DBSession, get_db, get_user
from core.security import authenticate_user, create_access_token, create_refresh_token, verify_token
from entities.auth.schema import Token, AccessTokenResponse, RefreshToken
from entities.common.models.model_user import User
from core.dependencies import get_current_user

router = APIRouter(
    prefix='/auth', 
    tags=['Auth']
)

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    settings = get_settings()

    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password", 
            headers={"WWW-Authenticate": "Bearer"}
            )
    
    # Create access and refresh tokens
    access_token = create_access_token(
        subject=user.id, 
        expires_delta=timedelta(minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
    
    refresh_token = create_refresh_token(
        subject=user.id, 
        expires_delta=timedelta(minutes = settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        )
    
    # By the OAuth2 convention we need to return seconds in the body. That is why conversion is needed here.
    access_token_expires = timedelta(minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    return Token(
        access_token=access_token, 
        refresh_token=refresh_token, 
        token_type="bearer", 
        expires_in=int(access_token_expires.total_seconds()),
        )

@router.post("/token/refresh",response_model=AccessTokenResponse)
def refresh_access_token(payload: RefreshToken, db: DBSession, user: User = Depends(get_current_user)) -> AccessTokenResponse:
    settings = get_settings()

    # Decode & validate
    try:
        token_data = verify_token(payload.refresh_token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = token_data.sub

    user = get_user(db, user_id=user_id)

    if not user or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token payload", 
            headers={"WWW-Authenticate": "Bearer"},)
    
    # Issue a new access token
    access_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user_id)

    return AccessTokenResponse ( 
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_expires.total_seconds())
    )
