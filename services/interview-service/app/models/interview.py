from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(255))
    job_title = Column(String(255))
    job_description = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True)
    difficulty_level = Column(String(20), nullable=True)  # easy, medium, hard
    interview_type = Column(String(50), nullable=True)  # technical, behavioral, mixed
    status = Column(String(20), default="draft")  # draft, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan")
    sessions = relationship("PracticeSession", back_populates="interview", cascade="all, delete-orphan") 