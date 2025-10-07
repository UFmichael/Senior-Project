from uuid import UUID
from .schemas import UserCreate
from entities.common.models.model_user import User
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional 
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_user(db: Session, user_id: UUID) -> Optional[User]:
    return db.get(User, user_id)

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()    

def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        username=user.username,
        hashed_password=bcrypt.hash(user.password)
    )
    db.add(db_user)

    try:
       db.commit()
       db.refresh(db_user) 
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with username {user.username} already exists"
        )
    return db_user