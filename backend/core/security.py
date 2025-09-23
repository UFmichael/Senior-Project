from uuid import UUID 
from fastapi import HTTPException, status
from datetime import timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from entities.common.models.model_user import User
from entities.user.services import get_user_by_username
from entities.auth.schema import TokenData
from core.config import get_settings
from utils.dates import aware_utcnow
from jose import jwt, JWTError, ExpiredSignatureError

import logging 
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)

    if user is None:
        logging.warning("Auth fail: Unknown username=%s", username)
        return None
    
    if not verify_password(password, user.hashed_password):
        logging.warning("Auth fail: Wrong password for username=%s", username)
        return None
    logger.info("User %s authenticated", username)
    return user

def create_access_token(subject: UUID, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()

    now = aware_utcnow()

    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token with:
      - 'sub'   : the user's UUID (stringified)
      - 'exp'   : expiration datetime
      - 'iat'   : issued-at datetime
      - 'type'  : 'refresh' marker
    """
    settings = get_settings()

    now = aware_utcnow()

    expire = now + (expires_delta or timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES))

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> TokenData:
    """
    Decode and validate a JWT against our SECRET_KEY and ALGORITHM.
    Requires 'exp' and 'sub' claims. Raises HTTPException(401) if invalid.
    Returns the TokenData object on succeed.
    """
    settings = get_settings()

    try:
        raw = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require_exp": True, "require_sub": True}
        )
        return TokenData.model_validate(raw)
    except ExpiredSignatureError:
        # Token was valid but it is now expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        # Includes signature invalid, missing claims, malformed, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

