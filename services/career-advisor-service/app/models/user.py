from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    
    # Profile fields
    skills = Column(JSON, nullable=True)  # List of skills
    experiences = Column(JSON, nullable=True)  # List of work experiences
    education = Column(JSON, nullable=True)  # List of educational background
    career_goals = Column(JSON, nullable=True)  # List of career goals
    preferred_industries = Column(JSON, nullable=True)  # List of preferred industries
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    career_profiles = relationship("CareerProfile", back_populates="user")
    cvs = relationship("CV", back_populates="user")