from datetime import datetime
from typing import List
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean
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
    career_advices = relationship("CareerAdvice", back_populates="user")

class CareerAdvice(Base):
    __tablename__ = "career_advice"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    cv_text = Column(Text)
    cv_embedding = Column(ARRAY(float))  # Store as array in PostgreSQL
    advice_history = Column(ARRAY(JSONB), default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Skills and interests extracted from CV
    skills = Column(ARRAY(String), default=[])
    interests = Column(ARRAY(String), default=[])
    
    # Career path recommendations
    career_paths = Column(JSONB, default={})
    
    # Analysis results
    strengths = Column(ARRAY(String), default=[])
    weaknesses = Column(ARRAY(String), default=[])
    improvement_areas = Column(JSONB, default={})

    # Status flags
    is_processed = Column(Boolean, default=False)
    processing_error = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="career_advices")

    @property
    def latest_advice(self):
        """Get the most recent career advice"""
        return self.advice_history[-1] if self.advice_history else None
