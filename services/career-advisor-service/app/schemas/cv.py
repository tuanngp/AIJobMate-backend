from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class CVBase(BaseModel):
    file_name: str
    file_type: str


class CVInDB(CVBase):
    id: int
    
    analysis_status: Optional[str] = None
    analysis_error: Optional[str] = None
    last_analyzed_at: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CVAnalysisResponse(BaseModel):
    status: str
    message: str
    
    
class PersonalInfo(BaseModel):
    name: str
    email: str
    phone: str
    location: str


class Education(BaseModel):
    degree: str
    institution: str
    year: str
    major: str
    achievements: List[str]


class Certification(BaseModel):
    name: str
    issuer: str
    year: str


class Experience(BaseModel):
    position: str
    company: str
    duration: str
    responsibilities: List[str]
    achievements: List[str]


class Skills(BaseModel):
    technical: List[str]
    soft: List[str]
    languages: List[str]


class CareerRecommendation(BaseModel):
    industry: str
    position: str
    description: str
    reason: str
    required_skills: List[str]
    required_experience: int
    score: float


class DevelopmentSuggestion(BaseModel):
    area: str
    suggestion: str
    resources: List[str]


class BasicAnalysis(BaseModel):
    experience_level: str
    strengths: List[str]
    weaknesses: List[str]
    career_recommendations: List[CareerRecommendation]
    career_goals: List[str]
    development_suggestions: List[DevelopmentSuggestion]


class SkillGap(BaseModel):
    skill: str
    importance: str
    reason: str


class CareerPath(BaseModel):
    path: str
    fit_score: float
    description: str


class RecommendedSkill(BaseModel):
    skill: str
    reason: str


class RecommendedAction(BaseModel):
    action: str
    priority: str
    description: str


class CareerMatch(BaseModel):
    id: str
    name: str
    description: str
    industry: str
    required_skills: List[str]
    required_experience: float
    similarity_score: float
    skill_match_score: float


class DetailedMetrics(BaseModel):
    action_verbs_used: int
    quantified_achievements: int
    avg_bullets_per_role: float
    keyword_density: float


class SectionScore(BaseModel):
    score: int
    feedback: List[str]


class SectionScores(BaseModel):
    personal_info: SectionScore
    education: SectionScore
    experience: SectionScore
    skills: SectionScore


class LanguageQuality(BaseModel):
    score: int
    strengths: List[str]
    improvements: List[str]


class ATSCompatibility(BaseModel):
    score: int
    issues: List[str]
    keywords_missing: List[str]
    format_suggestions: List[str]


class ImprovementPriority(BaseModel):
    area: str
    priority: str
    current_score: int
    potential_impact: float
    suggestions: List[str]


class Completeness(BaseModel):
    score: int
    missing_sections: List[str]
    improvement_suggestions: List[str]


class Formatting(BaseModel):
    score: int
    issues: List[str]
    positive_points: List[str]


class QualityAssessment(BaseModel):
    overall: float
    completeness: Completeness
    formatting: Formatting
    section_scores: SectionScores
    language_quality: LanguageQuality
    ats_compatibility: ATSCompatibility
    improvement_priority: List[ImprovementPriority]


class CareerAnalysis(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    skill_gaps: List[SkillGap]
    career_paths: List[CareerPath]
    recommended_skills: List[RecommendedSkill]
    recommended_actions: List[RecommendedAction]
    analysis_summary: str
    career_matches: List[CareerMatch]
    preferred_industries: List[str]


class BasicAnalysisResponse(BaseModel):
    personal_info: PersonalInfo
    education: List[Education]
    certifications: List[Certification]
    experiences: List[Experience]
    skills: Skills
    analysis: BasicAnalysis


class Metrics(BaseModel):
    detailed: DetailedMetrics
    word_count: int
    sections_count: int


class ResumeAnalysisResponse(BaseModel):
    status: str = Field(..., description="Analysis status, e.g., 'completed'")
    basic_analysis: BasicAnalysisResponse
    career_analysis: CareerAnalysis
    quality_assessment: QualityAssessment
    metrics: Metrics
    analysis_status: str
    last_analyzed_at: datetime
    created_at: datetime
    updated_at: datetime