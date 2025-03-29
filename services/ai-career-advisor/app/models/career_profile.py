from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class CareerProfile(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    title = Column(String(255))
    description = Column(Text)
    
    # Profile data
    skills = Column(JSON, nullable=True)  # List of skills
    experiences = Column(JSON, nullable=True)  # List of work experiences
    education = Column(JSON, nullable=True)  # List of educational background
    career_goals = Column(JSON, nullable=True)  # List of career goals
    preferred_industries = Column(JSON, nullable=True)  # List of preferred industries
    
    # Analysis results
    strengths = Column(JSON, nullable=True)  # List of identified strengths
    weaknesses = Column(JSON, nullable=True)  # List of identified weaknesses
    skill_gaps = Column(JSON, nullable=True)  # List of identified skill gaps
    recommended_career_paths = Column(JSON, nullable=True)  # List of recommended career paths
    recommended_skills = Column(JSON, nullable=True)  # List of recommended skills to develop
    recommended_actions = Column(JSON, nullable=True)  # List of recommended actions
    
    # Vector embedding for similarity search
    embedding_vector = Column(JSON, nullable=True)  # Vector representation of profile
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="career_profiles")