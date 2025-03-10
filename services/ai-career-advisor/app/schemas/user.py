from typing import Optional, List, Dict, Any
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

# Schema cho việc update user
class UserUpdate(UserBase):
    password: Optional[str] = None
    skills: Optional[List[str]] = None
    experiences: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    career_goals: Optional[List[str]] = None
    preferred_industries: Optional[List[str]] = None
    
    @validator("skills", "experiences", "education", "career_goals", "preferred_industries", pre=True)
    def json_serialize(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

# Schema cho việc đọc thông tin user
class UserInDBBase(UserBase):
    id: str
    skills: Optional[List[str]] = None
    experiences: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    career_goals: Optional[List[str]] = None
    preferred_industries: Optional[List[str]] = None
    
    @validator("skills", "experiences", "education", "career_goals", "preferred_industries", pre=True)
    def json_deserialize(cls, v):
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