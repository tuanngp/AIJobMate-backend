from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator

# Base Schemas
class UserBase(BaseModel):
    email: EmailStr
    profile: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Job Schemas
class Location(BaseModel):
    city: str
    state: Optional[str] = None
    country: str
    coordinates: Optional[Dict[str, float]] = None

class SalaryRange(BaseModel):
    min: int
    max: int
    currency: str = "USD"
    period: str = "yearly"  # yearly, monthly, hourly

class CompanyInfo(BaseModel):
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    linkedin_url: Optional[str] = None

class JobBase(BaseModel):
    title: str
    company: str
    location: Union[str, Location]
    description: str
    requirements: str
    job_type: str
    experience_level: Optional[str] = None
    education_level: Optional[str] = None
    industry: Optional[str] = None
    function: Optional[str] = None
    salary: Optional[SalaryRange] = None
    remote_type: Optional[str] = None
    remote_percentage: Optional[int] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)

class JobCreate(JobBase):
    source: str
    source_url: str
    source_id: Optional[str] = None
    company_info: Optional[CompanyInfo] = None

class JobUpdate(JobBase):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

class Job(JobBase):
    id: UUID
    normalized_title: Optional[str] = None
    job_category: Optional[str] = None
    extracted_skills: Dict[str, Any] = Field(default_factory=dict)
    analyzed_requirements: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool
    is_verified: bool
    posted_at: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Skill Schemas
class SkillLevel(BaseModel):
    level: int = Field(ge=1, le=5)
    years: float
    certifications: List[str] = Field(default_factory=list)

class SkillEndorsement(BaseModel):
    endorser_id: UUID
    level: int
    comment: Optional[str] = None
    created_at: datetime

class SkillBase(BaseModel):
    name: str
    category: str
    subcategory: Optional[str] = None
    type: str  # technical, soft, domain
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    related_skills: List[str] = Field(default_factory=list)

class SkillCreate(SkillBase):
    pass

class Skill(SkillBase):
    id: UUID
    demand_score: Optional[float] = None
    salary_impact: Optional[float] = None
    growth_trend: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Job Preference Schemas
class JobPreferenceBase(BaseModel):
    desired_titles: List[str] = Field(default_factory=list)
    desired_industries: List[str] = Field(default_factory=list)
    desired_functions: List[str] = Field(default_factory=list)
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    salary_currency: str = "USD"
    locations: List[str] = Field(default_factory=list)
    remote_preference: Optional[str] = None
    willing_to_relocate: bool = False
    max_commute_distance: Optional[int] = None
    years_experience: Optional[int] = None
    education_level: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    job_types: List[str] = Field(default_factory=list)
    work_schedule: Dict[str, Any] = Field(default_factory=dict)
    company_sizes: List[str] = Field(default_factory=list)
    benefits_required: List[str] = Field(default_factory=list)

class JobPreferenceCreate(JobPreferenceBase):
    user_id: UUID

class JobPreference(JobPreferenceBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Job Application Schemas
class JobApplicationBase(BaseModel):
    status: str
    source: str
    notes: Optional[str] = None

class JobApplicationCreate(JobApplicationBase):
    user_id: UUID
    job_id: UUID

class JobApplication(JobApplicationBase):
    id: UUID
    user_id: UUID
    job_id: UUID
    match_score: Optional[float] = None
    skill_match: Dict[str, Any] = Field(default_factory=dict)
    requirements_match: Dict[str, Any] = Field(default_factory=dict)
    stages: List[Dict[str, Any]] = Field(default_factory=list)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    application_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Job Match Schemas
class JobMatchBase(BaseModel):
    overall_score: float = Field(ge=0, le=1)
    skill_score: float = Field(ge=0, le=1)
    experience_score: float = Field(ge=0, le=1)
    location_score: float = Field(ge=0, le=1)
    salary_match: Optional[float] = Field(None, ge=0, le=1)

class JobMatchCreate(JobMatchBase):
    user_id: UUID
    job_id: UUID
    matched_skills: Dict[str, Any]
    missing_skills: List[str]
    skill_gaps: Dict[str, Any]
    match_factors: Dict[str, Any]
    recommendations: Dict[str, Any]

class JobMatch(JobMatchBase):
    id: UUID
    user_id: UUID
    job_id: UUID
    matched_skills: Dict[str, Any]
    missing_skills: List[str]
    skill_gaps: Dict[str, Any]
    match_factors: Dict[str, Any]
    recommendations: Dict[str, Any]
    is_viewed: bool
    is_saved: bool
    user_feedback: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Search and Filter Schemas
class JobSearchParams(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    remote_only: bool = False
    job_types: Optional[List[str]] = None
    experience_levels: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    min_salary: Optional[int] = None
    posted_within_days: Optional[int] = None
    skills: Optional[List[str]] = None
    company_sizes: Optional[List[str]] = None
    sort_by: str = "relevance"  # relevance, date, salary
    page: int = 1
    page_size: int = 20

class JobSearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[Job]
    facets: Dict[str, Any]
    suggestions: Dict[str, Any]

# Recommendation Schemas
class JobRecommendation(BaseModel):
    job: Job
    match_score: float
    match_reasons: List[str]
    skill_match: Dict[str, float]
    missing_skills: List[str]
    salary_comparison: Optional[Dict[str, Any]] = None
    market_insights: Dict[str, Any]

class RecommendationResponse(BaseModel):
    recommendations: List[JobRecommendation]
    total_matches: int
    market_trends: Dict[str, Any]
    skill_suggestions: Dict[str, Any]
    career_path_suggestions: List[Dict[str, Any]]

# Analysis Schemas
class SkillGapAnalysis(BaseModel):
    missing_critical_skills: List[str]
    missing_preferred_skills: List[str]
    skill_proficiency_gaps: Dict[str, float]
    recommended_learning_paths: List[Dict[str, Any]]
    estimated_time_to_acquire: Dict[str, str]

class MarketAnalysis(BaseModel):
    demand_level: str
    growth_rate: float
    salary_range: SalaryRange
    top_employers: List[str]
    required_skills_frequency: Dict[str, float]
    location_opportunities: Dict[str, int]
