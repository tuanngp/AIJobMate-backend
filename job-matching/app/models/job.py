from datetime import datetime
from typing import List
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    profile = Column(JSONB, default={})
    preferences = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job_preferences = relationship("JobPreference", back_populates="user")
    job_applications = relationship("JobApplication", back_populates="user")
    skill_profiles = relationship("UserSkillProfile", back_populates="user")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic job information
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    location = Column(String)
    description = Column(String)
    requirements = Column(String)
    
    # Job details
    job_type = Column(String)  # full-time, part-time, contract, etc.
    experience_level = Column(String)
    education_level = Column(String)
    industry = Column(String, index=True)
    function = Column(String)
    
    # Salary information
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String, default="USD")
    salary_period = Column(String, default="yearly")  # yearly, monthly, hourly
    
    # Remote work
    remote_type = Column(String)  # no, hybrid, full
    remote_percentage = Column(Integer)
    
    # Skills and requirements
    required_skills = Column(ARRAY(String), default=[])
    preferred_skills = Column(ARRAY(String), default=[])
    skill_weights = Column(JSONB, default={})  # Importance weights for skills
    
    # Job posting details
    source = Column(String)  # linkedin, indeed, etc.
    source_url = Column(String)
    source_id = Column(String)
    posted_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Company details
    company_info = Column(JSONB, default={})
    company_industry = Column(String)
    company_size = Column(String)
    
    # Analysis results
    embedding = Column(ARRAY(Float))  # Job description embedding
    normalized_title = Column(String)
    job_category = Column(String)
    extracted_skills = Column(JSONB, default={})
    analyzed_requirements = Column(JSONB, default={})
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_checked = Column(DateTime)
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = relationship("JobApplication", back_populates="job")
    matches = relationship("JobMatch", back_populates="job")

class JobPreference(Base):
    __tablename__ = "job_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Job preferences
    desired_titles = Column(ARRAY(String), default=[])
    desired_industries = Column(ARRAY(String), default=[])
    desired_functions = Column(ARRAY(String), default=[])
    min_salary = Column(Integer)
    max_salary = Column(Integer)
    salary_currency = Column(String, default="USD")
    
    # Location preferences
    locations = Column(ARRAY(String), default=[])
    remote_preference = Column(String)  # no, hybrid, full
    willing_to_relocate = Column(Boolean, default=False)
    max_commute_distance = Column(Integer)  # in kilometers
    
    # Experience and skills
    years_experience = Column(Integer)
    education_level = Column(String)
    skills = Column(ARRAY(String), default=[])
    skill_levels = Column(JSONB, default={})
    
    # Job type preferences
    job_types = Column(ARRAY(String), default=[])  # full-time, part-time, etc.
    work_schedule = Column(JSONB, default={})
    
    # Additional preferences
    company_sizes = Column(ARRAY(String), default=[])
    benefits_required = Column(ARRAY(String), default=[])
    culture_preferences = Column(JSONB, default={})
    
    # Weights for matching
    preference_weights = Column(JSONB, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="job_preferences")

class UserSkillProfile(Base):
    __tablename__ = "user_skill_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Skills assessment
    skills = Column(JSONB, default={})  # {skill: {level, years, certifications}}
    skill_categories = Column(JSONB, default={})
    skill_endorsements = Column(JSONB, default={})
    
    # Experience
    work_history = Column(JSONB, default=[])
    projects = Column(JSONB, default=[])
    education = Column(JSONB, default=[])
    certifications = Column(JSONB, default=[])
    
    # Skill vectors
    skill_embedding = Column(ARRAY(Float))
    category_weights = Column(JSONB, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="skill_profiles")

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    
    # Application details
    status = Column(String)  # applied, interviewing, offered, rejected, etc.
    application_date = Column(DateTime)
    source = Column(String)
    
    # Matching and scoring
    match_score = Column(Float)
    skill_match = Column(JSONB, default={})
    requirements_match = Column(JSONB, default={})
    
    # Application tracking
    stages = Column(JSONB, default=[])
    feedback = Column(JSONB, default={})
    notes = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="job_applications")
    job = relationship("Job", back_populates="applications")

class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"))
    
    # Match scores
    overall_score = Column(Float)
    skill_score = Column(Float)
    experience_score = Column(Float)
    location_score = Column(Float)
    salary_match = Column(Float)
    
    # Detailed matching
    matched_skills = Column(JSONB, default={})
    missing_skills = Column(ARRAY(String), default=[])
    skill_gaps = Column(JSONB, default={})
    
    # Match analysis
    match_factors = Column(JSONB, default={})
    recommendations = Column(JSONB, default={})
    
    # Status
    is_viewed = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False)
    user_feedback = Column(JSONB, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="matches")

class SkillTaxonomy(Base):
    __tablename__ = "skill_taxonomy"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    
    # Skill classification
    category = Column(String)
    subcategory = Column(String)
    type = Column(String)  # technical, soft, domain, etc.
    
    # Skill details
    description = Column(String)
    aliases = Column(ARRAY(String), default=[])
    related_skills = Column(ARRAY(String), default=[])
    
    # Skill requirements
    typical_experience_levels = Column(JSONB, default={})
    certifications = Column(ARRAY(String), default=[])
    learning_resources = Column(JSONB, default=[])
    
    # Market data
    demand_score = Column(Float)
    salary_impact = Column(Float)
    growth_trend = Column(String)
    
    # Embedding and matching
    embedding = Column(ARRAY(Float))
    verification_rules = Column(JSONB, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
