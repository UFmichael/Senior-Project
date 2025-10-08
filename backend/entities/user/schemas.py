from pydantic import BaseModel,  Field 
from uuid import UUID 

class UserBase(BaseModel):
    username: str 

class UserCreate(UserBase): 
    password: str = Field(min_length=8, max_length=72, description="Bcrypt supports up to 72 characters") 

class PasswordChange(BaseModel): 
    current_password: str = Field(
        min_length=8, 
        description="Old password"
    )
    new_password: str = Field(
        min_length=8, 
        description="New password"
    )

class UserRead(BaseModel): 
    id: UUID 
    disabled: bool | None = None

    model_config = {
        "from_attributes": True
    }