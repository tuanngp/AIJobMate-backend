from datetime import datetime
from typing import List
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Float, Boolean
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
    video_sessions = relationship("VideoSession", back_populates="user")

class VideoSession(Base):
    __tablename__ = "video_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Video details
    video_url = Column(String)
    thumbnail_url = Column(String)
    duration = Column(Float)  # in seconds
    file_format = Column(String)
    frame_count = Column(Integer)
    resolution = Column(JSONB)  # {width: int, height: int}
    
    # Interview context
    interview_type = Column(String)  # e.g., "behavioral", "technical"
    job_role = Column(String)
    
    # Facial analysis
    facial_expressions = Column(JSONB, default={})  # Time-series of expressions
    emotion_scores = Column(JSONB, default={})  # Aggregated emotion scores
    eye_contact_metrics = Column(JSONB, default={})  # Eye contact analysis
    
    # Body language analysis
    posture_analysis = Column(JSONB, default={})  # Posture assessment
    gesture_analysis = Column(JSONB, default={})  # Hand gesture analysis
    movement_patterns = Column(JSONB, default={})  # Overall movement analysis
    
    # Frame analysis
    key_frames = Column(ARRAY(String))  # URLs of important frames
    frame_embeddings = Column(ARRAY(Float))  # CLIP embeddings
    frame_timestamps = Column(ARRAY(Float))  # Timestamps of analyzed frames
    
    # Performance metrics
    confidence_score = Column(Float)  # 0-100
    engagement_score = Column(Float)  # 0-100
    professionalism_score = Column(Float)  # 0-100
    overall_score = Column(Float)  # 0-100
    
    # Analysis results
    strengths = Column(ARRAY(String), default=[])
    weaknesses = Column(ARRAY(String), default=[])
    improvement_areas = Column(JSONB, default={})
    recommendations = Column(ARRAY(String), default=[])
    
    # Detailed feedback
    feedback = Column(JSONB, default={})
    section_scores = Column(JSONB, default={})
    practice_suggestions = Column(JSONB, default={})
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_error = Column(String, nullable=True)
    processing_status = Column(JSONB, default={})  # Detailed processing status
    
    # Analysis metadata
    analysis_version = Column(String)  # Version of analysis models used
    analysis_settings = Column(JSONB, default={})  # Settings used for analysis
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Cache control
    cache_version = Column(Integer, default=1)
    last_accessed = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="video_sessions")

    @property
    def summary(self):
        """Get a summary of the video session"""
        return {
            "id": str(self.id),
            "duration": self.duration,
            "interview_type": self.interview_type,
            "job_role": self.job_role,
            "overall_score": self.overall_score,
            "key_strengths": self.strengths[:3],  # Top 3 strengths
            "main_improvements": list(self.improvement_areas.keys())[:3],  # Top 3 areas
            "created_at": self.created_at.isoformat(),
            "status": "processed" if self.is_processed else "processing"
        }

    @property
    def performance_summary(self):
        """Get a summary of performance metrics"""
        return {
            "confidence": self.confidence_score,
            "engagement": self.engagement_score,
            "professionalism": self.professionalism_score,
            "overall": self.overall_score,
            "section_scores": self.section_scores
        }
