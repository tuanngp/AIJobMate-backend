from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from pydantic import BaseModel, EmailStr, field_serializer

if TYPE_CHECKING:
    from .user import Role  # for type hints

# Association table for user roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    users = relationship("User", secondary=user_roles, back_populates="roles")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    roles = relationship("Role", secondary=user_roles, back_populates="users")

# Pydantic models for request/response
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    roles: List[str] = ["user"]

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
class UserInDBBase(UserBase):
    id: int
    disabled: bool = False
    created_at: datetime
    updated_at: datetime
    roles: List[str]

    class Config:
        from_attributes = True

    @field_serializer('roles')
    def serialize_roles(self, roles: List['Role']) -> List[str]:
        return [role.name for role in (roles or [])]



class UserResponse(UserInDBBase):
    pass

class UserInDB(UserInDBBase):
    hashed_password: str