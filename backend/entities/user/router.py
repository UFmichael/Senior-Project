from entities.user.schemas import UserCreate, UserRead
from fastapi import APIRouter, Depends, HTTPException, status 
from uuid import UUID
from entities.user import services as user_services
from sqlalchemy.orm import Session
from entities.common.models.model_user import User
from core.dependencies import get_db,  get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_route(user: UserCreate, db: Session = Depends(get_db)):
    if user_services.get_user_by_username(db, username=user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    return user_services.create_user(db=db, user=user)