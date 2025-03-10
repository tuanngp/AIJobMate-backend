from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, validator
import json

# Schemas cho CareerProfile
class CareerProfileBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

# Schema cho việc tạo career profile
class CareerProfileCreate(CareerProfileBase):
    title: str
    user_id: Optional[str] = None  # Sẽ được lấy từ token

# Schema cho việc update career profile
class CareerProfileUpdate(CareerProfileBase):
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    skill_gaps: Optional[List[Dict[str, Any]]] = None
    recommended_career_paths: Optional[List[Dict[str, Any]]] = None
    recommended_skills: Optional[List[Dict[str, Any]]] = None
    recommended_actions: Optional[List[Dict[str, Any]]] = None
    
    @validator("strengths", "weaknesses", "skill_gaps", "recommended_career_paths", 
               "recommended_skills", "recommended_actions", pre=True)
    def json_serialize(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

# Schema cho việc đọc thông tin career profile
class CareerProfileInDBBase(CareerProfileBase):
    id: str
    user_id: str
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    skill_gaps: Optional[List[Dict[str, Any]]] = None
    recommended_career_paths: Optional[List[Dict[str, Any]]] = None
    recommended_skills: Optional[List[Dict[str, Any]]] = None
    recommended_actions: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @validator("strengths", "weaknesses", "skill_gaps", "recommended_career_paths", 
               "recommended_skills", "recommended_actions", pre=True)
    def json_deserialize(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        orm_mode = True

# Schema để trả về từ API
class CareerProfile(CareerProfileInDBBase):
    pass

# Schemas cho CareerPathway
class CareerPathwayBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: str

# Schema cho việc tạo career pathway
class CareerPathwayCreate(CareerPathwayBase):
    required_skills: List[str]
    required_experience: int
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    growth_potential: Optional[float] = None
    
    @validator("required_skills", pre=True)
    def json_serialize(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

# Schema cho việc update career pathway
class CareerPathwayUpdate(CareerPathwayBase):
    required_skills: Optional[List[str]] = None
    required_experience: Optional[int] = None
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    growth_potential: Optional[float] = None
    
    @validator("required_skills", pre=True)
    def json_serialize(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

# Schema cho việc đọc thông tin career pathway
class CareerPathwayInDBBase(CareerPathwayBase):
    id: str
    required_skills: List[str]
    required_experience: int
    salary_range_min: Optional[float] = None
    salary_range_max: Optional[float] = None
    growth_potential: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @validator("required_skills", pre=True)
    def json_deserialize(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        orm_mode = True

# Schema để trả về từ API
class CareerPathway(CareerPathwayInDBBase):
    pass

# Schemas cho các request đặc biệt
class CareerAnalysisRequest(BaseModel):
    profile_id: Optional[str] = None
    skills: Optional[List[str]] = None
    experiences: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    career_goals: Optional[List[str]] = None
    preferred_industries: Optional[List[str]] = None

class CareerRecommendationResponse(BaseModel):
    career_paths: List[Dict[str, Any]]
    skills_to_develop: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    analysis_summary: str

class SkillGapResponse(BaseModel):
    current_skills: List[str]
    missing_skills: List[Dict[str, Any]]
    skill_gap_score: float
    recommendations: List[Dict[str, Any]] 