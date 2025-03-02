from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    profile: Dict[str, Any] = Field(default_factory=dict)

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Interview Session Schemas
class InterviewConfig(BaseModel):
    interview_type: str = Field(..., description="Type of interview (behavioral/technical)")
    job_role: str = Field(..., description="Target job role")
    questions: List[str] = Field(default_factory=list)
    language: str = Field(default="en", description="Interview language")

class AudioMetadata(BaseModel):
    duration: float
    file_format: str
    sample_rate: int = Field(default=16000)

class SpeechMetrics(BaseModel):
    pace: float = Field(..., description="Words per minute")
    clarity: float = Field(..., description="Speech clarity score (0-100)")
    filler_words_count: int
    filler_words: List[Dict[str, Any]]
    pauses: List[Dict[str, float]]
    tone_variations: Dict[str, float]

class SentimentAnalysis(BaseModel):
    confidence: float
    enthusiasm: float
    stress_level: float
    emotions: Dict[str, float]

class ContentAnalysis(BaseModel):
    relevance: float
    completeness: float
    structure: float
    key_points: List[str]
    missing_points: List[str]
    technical_accuracy: Optional[float] = None

class PerformanceMetrics(BaseModel):
    clarity_score: float = Field(..., ge=0, le=100)
    content_score: float = Field(..., ge=0, le=100)
    confidence_score: float = Field(..., ge=0, le=100)
    overall_score: float = Field(..., ge=0, le=100)

class InterviewSessionBase(BaseModel):
    user_id: Optional[UUID] = None
    interview_type: str
    job_role: str
    questions: List[str] = Field(default_factory=list)
    language: str = "en"

class InterviewSessionCreate(InterviewSessionBase):
    pass

class InterviewSessionUpdate(InterviewSessionBase):
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    speech_metrics: Optional[Dict[str, Any]] = None
    sentiment_analysis: Optional[Dict[str, Any]] = None
    content_analysis: Optional[Dict[str, Any]] = None
    improvement_areas: Optional[Dict[str, Any]] = None

class InterviewSession(InterviewSessionBase):
    id: UUID
    audio_url: str
    duration: float
    file_format: str
    transcript: Optional[str] = None
    speech_metrics: Dict[str, Any]
    sentiment_analysis: Dict[str, Any]
    content_analysis: Dict[str, Any]
    key_points: List[str]
    improvement_areas: Dict[str, Any]
    feedback: str
    recommendations: List[str]
    practice_suggestions: Dict[str, Any]
    is_processed: bool
    processing_error: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    performance_metrics: PerformanceMetrics
    total_questions: int
    total_duration: float
    cache_version: int
    last_accessed: datetime

    model_config = ConfigDict(from_attributes=True)

# Request/Response Schemas
class AudioUploadResponse(BaseModel):
    session_id: UUID
    audio_url: str
    estimated_duration: float
    file_format: str

class InterviewAnalysisResponse(BaseModel):
    session_id: UUID
    transcript: str
    speech_analysis: Dict[str, Any]
    content_analysis: Dict[str, Any]
    feedback: str
    performance_metrics: PerformanceMetrics
    recommendations: List[str]
    practice_suggestions: Dict[str, Any]
    processing_time: float

class InterviewSessionSummary(BaseModel):
    id: UUID
    interview_type: str
    job_role: str
    duration: float
    overall_score: float
    key_improvements: List[str]
    created_at: datetime

class InterviewProgress(BaseModel):
    total_sessions: int
    average_score: float
    top_strengths: List[str]
    common_improvements: List[str]
    score_history: List[Dict[str, Union[datetime, float]]]
    practice_recommendations: List[str]

# Batch Operation Schemas
class BatchProcessingResponse(BaseModel):
    success: bool
    processed_count: int
    failed_count: int
    errors: List[Dict[str, str]]

# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
