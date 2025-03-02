from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Base Schemas
class UserBase(BaseModel):
    email: EmailStr
    profile: Dict[str, Any] = Field(default_factory=dict)

class UserCreate(UserBase):
    pass

class UserUpdate(UserBase):
    email: Optional[EmailStr] = None

class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Career Advice Schemas
class CareerAdviceBase(BaseModel):
    user_id: Optional[UUID] = None
    skills: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)

class CVUpload(BaseModel):
    file_content: str
    file_name: str

class CareerAdviceCreate(CareerAdviceBase):
    cv_text: str

class CareerAdviceUpdate(CareerAdviceBase):
    cv_text: Optional[str] = None
    career_paths: Optional[Dict[str, Any]] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    improvement_areas: Optional[Dict[str, Any]] = None

class CareerAdvice(CareerAdviceBase):
    id: UUID
    cv_text: str
    advice_history: List[Dict[str, Any]]
    career_paths: Dict[str, Any]
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: Dict[str, Any]
    is_processed: bool
    processing_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Response Schemas
class CareerAnalysisResponse(BaseModel):
    skills_analysis: Dict[str, Any] = Field(
        description="Analysis of skills from CV"
    )
    career_suggestions: List[Dict[str, Any]] = Field(
        description="Career path suggestions"
    )
    improvement_recommendations: Dict[str, Any] = Field(
        description="Areas for improvement"
    )

class JobPreferences(BaseModel):
    desired_role: str
    desired_industry: Optional[str] = None
    experience_level: Optional[str] = None
    location_preference: Optional[str] = None
    salary_expectation: Optional[Dict[str, float]] = None
    remote_preference: Optional[str] = None

class CareerAdviceRequest(BaseModel):
    preferences: JobPreferences
    additional_context: Optional[str] = None

class CareerAdviceResponse(BaseModel):
    advice: str
    career_paths: List[Dict[str, Any]]
    skills_gap: Dict[str, Any]
    next_steps: List[str]
    resources: List[Dict[str, str]]

# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None

# Batch Operation Schemas
class BatchProcessingResponse(BaseModel):
    success: bool
    processed_count: int
    failed_count: int
    errors: List[Dict[str, str]]
