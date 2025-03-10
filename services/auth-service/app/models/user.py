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
    
    # Thông tin profile cơ bản của người dùng
    # Thay vì lưu các trường này trực tiếp, chúng ta chỉ lưu ID và metadata
    # Chi tiết sẽ được lưu trong các service khác
    profile_metadata = Column(String)  # JSON để lưu metadata về profile 