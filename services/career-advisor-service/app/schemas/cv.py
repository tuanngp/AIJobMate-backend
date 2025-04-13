from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class CVBase(BaseModel):
    file_name: str
    file_type: str


class CVCreate(CVBase):
    pass


class CVUpdate(CVBase):
    extracted_text: Optional[str] = None


class CareerPath(BaseModel):
    role: str
    confidence: float
    reasons: List[str]
    requirements: List[str]
    salary_range: Optional[Dict[str, float]]


class SkillGap(BaseModel):
    skill: str
    importance: str
    development_suggestion: str


class CareerAnalysis(BaseModel):
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    skill_gaps: Optional[List[SkillGap]] = None
    recommended_careers: Optional[List[CareerPath]] = None
    recommended_skills: Optional[List[Dict[str, str]]] = None
    recommended_actions: Optional[List[Dict[str, str]]] = None
    last_analyzed_at: Optional[datetime] = None


class CVInDB(CVBase):
    id: int
    user_id: int
    original_content: Optional[str] = None
    extracted_text: str
    
    # Profile data
    skills: Optional[List[str]] = None
    experiences: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    career_goals: Optional[List[str]] = None
    preferred_industries: Optional[List[str]] = None
    
    # Analysis results
    analysis_status: Optional[str] = None
    analysis_error: Optional[str] = None
    analysis_task_id: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CV(CVInDB):
    career_analysis: Optional[CareerAnalysis] = None


class CVAnalysisResponse(BaseModel):
    status: str
    message: str


class CVAnalysisResult(BaseModel):
    status: str
    career_analysis: CareerAnalysis
    last_analyzed_at: Optional[datetime] = None
