from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, field_serializer
from app.models.user import Role

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    roles: List[str] = ["user"]

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    
class UserInDBBase(UserBase):
    id: int
    disabled: bool = False
    created_at: datetime
    updated_at: datetime
    roles: List[Role]

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

    @field_serializer('roles')
    def serialize_roles(self, roles: List[Role], _info) -> List[str]:
        if not roles:
            return []
        return [role.name for role in roles]


class UserInDB(UserInDBBase):
    hashed_password: str
    
class UserResponse(UserInDBBase):
    pass