from uuid import UUID
from entities.common.models.model_user import User
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, List


def get_user(db: Session, user_id: UUID) -> Optional[User]:
    return db.get(User, user_id)

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()    