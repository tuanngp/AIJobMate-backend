from datetime import datetime
from typing import List
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    profile = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="user")

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Audio file details
    audio_url = Column(String)
    duration = Column(Float)  # in seconds
    file_format = Column(String)
    
    # Interview context
    interview_type = Column(String)  # e.g., "behavioral", "technical"
    job_role = Column(String)
    questions = Column(ARRAY(String))
    
    # Analysis results
    transcript = Column(Text)  # Full speech-to-text transcript
    
    # Speech analysis
    speech_metrics = Column(JSONB, default={})  # Pace, clarity, filler words, etc.
    sentiment_analysis = Column(JSONB, default={})  # Confidence, enthusiasm, etc.
    
    # Content analysis
    content_analysis = Column(JSONB, default={})  # Answer quality, relevance, etc.
    key_points = Column(ARRAY(String), default=[])
    improvement_areas = Column(JSONB, default={})
    
    # Recommendations
    feedback = Column(Text)
    recommendations = Column(ARRAY(String), default=[])
    practice_suggestions = Column(JSONB, default={})
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Performance metrics
    clarity_score = Column(Float)  # 0-100
    content_score = Column(Float)  # 0-100
    confidence_score = Column(Float)  # 0-100
    overall_score = Column(Float)  # 0-100

    # Session metadata
    total_questions = Column(Integer, default=0)
    total_duration = Column(Float, default=0.0)  # in seconds
    language = Column(String, default="en")
    
    # Cache control
    cache_version = Column(Integer, default=1)
    last_accessed = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="interview_sessions")

    @property
    def summary(self):
        """Get a summary of the interview session"""
        return {
            "id": str(self.id),
            "duration": self.duration,
            "overall_score": self.overall_score,
            "key_points": self.key_points[:3],  # Top 3 key points
            "main_improvements": list(self.improvement_areas.keys())[:3],  # Top 3 areas
            "created_at": self.created_at.isoformat()
        }
