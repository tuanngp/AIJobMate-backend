from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, validator
import json

# Các schemas cơ bản
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

# Schema cho việc tạo user
class UserCreate(UserBase):
    email: EmailStr
    password: str
    profile_metadata: Optional[Dict[str, Any]] = None
    
    @validator("profile_metadata", pre=True)
    def validate_profile_metadata(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

# Schema cho việc update user
class UserUpdate(UserBase):
    password: Optional[str] = None
    profile_metadata: Optional[Dict[str, Any]] = None
    
    @validator("profile_metadata", pre=True)
    def validate_profile_metadata(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

# Schema cho việc đọc thông tin user
class UserInDBBase(UserBase):
    id: str
    profile_metadata: Optional[Dict[str, Any]] = None
    
    @validator("profile_metadata", pre=True)
    def validate_profile_metadata(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        orm_mode = True

# Schema để trả về từ API
class User(UserInDBBase):
    pass

# Schema chỉ sử dụng trong DB
class UserInDB(UserInDBBase):
    hashed_password: str 