from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Trường thông tin người dùng cho tư vấn nghề nghiệp
    skills = Column(String)                # Kỹ năng hiện có (JSON)
    experiences = Column(String)           # Kinh nghiệm làm việc (JSON)
    education = Column(String)             # Thông tin học vấn (JSON)
    career_goals = Column(String)          # Mục tiêu nghề nghiệp (JSON)
    preferred_industries = Column(String)  # Ngành công nghiệp ưa thích (JSON) 