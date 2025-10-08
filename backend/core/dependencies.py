from typing import Generator
from core.database import get_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from core.security import verify_token
from entities.common.models.model_user import User
from entities.user.services import get_user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

#region DB 
def get_db() -> Generator[Session, None, None]:

    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# DBSession dependency it works with Annotad 
DBSession = Annotated[Session, Depends(get_db)]

#endregion

#region User
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token)
    
    try:
        user_id = token_data.sub
    except (ValueError, TypeError):
        raise credentials_exception
    user = get_user(db, user_id=user_id)

    if not user:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    return current_user

