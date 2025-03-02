from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Base Schemas
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

# Video Analysis Schemas
class Resolution(BaseModel):
    width: int
    height: int

class FacialExpression(BaseModel):
    timestamp: float
    emotions: Dict[str, float]
    eye_contact: float
    head_pose: Dict[str, float]

class PostureMetrics(BaseModel):
    timestamp: float
    alignment: float
    stability: float
    position: Dict[str, float]

class GestureAnalysis(BaseModel):
    timestamp: float
    gesture_type: str
    confidence: float
    description: str

class PerformanceMetrics(BaseModel):
    confidence_score: float = Field(..., ge=0, le=100)
    engagement_score: float = Field(..., ge=0, le=100)
    professionalism_score: float = Field(..., ge=0, le=100)
    overall_score: float = Field(..., ge=0, le=100)
    section_scores: Dict[str, float]

class AnalysisSettings(BaseModel):
    analyze_facial_expressions: bool = True
    analyze_body_language: bool = True
    analyze_eye_contact: bool = True
    analyze_gestures: bool = True
    frame_extraction_rate: int = 1

# Session Schemas
class VideoSessionBase(BaseModel):
    user_id: Optional[UUID] = None
    interview_type: str
    job_role: str

class VideoSessionCreate(VideoSessionBase):
    analysis_settings: Optional[AnalysisSettings] = None

class VideoSessionUpdate(VideoSessionBase):
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    is_processed: Optional[bool] = None
    processing_status: Optional[Dict[str, Any]] = None

class VideoSession(VideoSessionBase):
    id: UUID
    video_url: str
    thumbnail_url: Optional[str]
    duration: float
    file_format: str
    frame_count: int
    resolution: Resolution
    
    facial_expressions: Dict[str, Any]
    emotion_scores: Dict[str, float]
    eye_contact_metrics: Dict[str, Any]
    
    posture_analysis: Dict[str, Any]
    gesture_analysis: Dict[str, Any]
    movement_patterns: Dict[str, Any]
    
    key_frames: List[str]
    frame_timestamps: List[float]
    
    performance_metrics: PerformanceMetrics
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: Dict[str, Any]
    recommendations: List[str]
    
    feedback: Dict[str, Any]
    practice_suggestions: Dict[str, Any]
    
    is_processed: bool
    processing_error: Optional[str]
    processing_status: Dict[str, Any]
    
    analysis_version: str
    analysis_settings: AnalysisSettings
    
    created_at: datetime
    processed_at: Optional[datetime]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Response Schemas
class VideoUploadResponse(BaseModel):
    session_id: UUID
    video_url: str
    thumbnail_url: Optional[str]
    duration: float
    file_format: str
    resolution: Resolution

class VideoAnalysisResponse(BaseModel):
    session_id: UUID
    performance_metrics: PerformanceMetrics
    facial_analysis: Dict[str, Any]
    body_language_analysis: Dict[str, Any]
    key_moments: List[Dict[str, Any]]
    feedback: Dict[str, Any]
    recommendations: List[str]
    practice_suggestions: Dict[str, Any]
    processing_time: float

class VideoSessionSummary(BaseModel):
    id: UUID
    interview_type: str
    job_role: str
    duration: float
    overall_score: float
    key_strengths: List[str]
    main_improvements: List[str]
    thumbnail_url: Optional[str]
    created_at: datetime
    status: str

class VideoProgress(BaseModel):
    total_sessions: int
    average_scores: Dict[str, float]
    top_strengths: List[str]
    common_improvements: List[str]
    score_history: List[Dict[str, Union[datetime, float]]]
    practice_recommendations: List[str]
    improvement_trends: Dict[str, List[float]]

# Request Schemas
class AnalysisRequest(BaseModel):
    focus_areas: Optional[List[str]] = None
    custom_metrics: Optional[Dict[str, Any]] = None
    feedback_preferences: Optional[Dict[str, bool]] = None

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
    context: Optional[Dict[str, Any]] = None
