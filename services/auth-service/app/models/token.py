from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.database import Base

class RefreshTokenDB(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class RevokedTokenDB(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)

# Pydantic models for request/response
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: int  # user id
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"
    roles: list[str]

class TokenData(BaseModel):
    user_id: int
    roles: list[str]

class RefreshToken(BaseModel):
    refresh_token: str

class RevokedToken(BaseModel):
    jti: str
    user_id: int
    expires_at: datetime
    revoked_at: datetime = datetime.utcnow()
    reason: Optional[str] = None

    class Config:
        from_attributes = True