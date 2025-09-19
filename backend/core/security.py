from uuid import UUID 
from datetime import timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from entities.common.models.model_user import User
from entities.user.services import get_user_by_username

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

