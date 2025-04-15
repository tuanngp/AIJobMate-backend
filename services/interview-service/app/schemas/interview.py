from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# Interview Question Schema
class InterviewQuestionBase(BaseModel):
    question: str
    question_type: str
    difficulty: str
    category: Optional[str] = None
    sample_answer: Optional[str] = None

class InterviewQuestionCreate(InterviewQuestionBase):
    pass

class InterviewQuestionUpdate(InterviewQuestionBase):
    ai_feedback: Optional[str] = None
    user_answer: Optional[str] = None

class InterviewQuestion(InterviewQuestionBase):
    id: int
    interview_id: int
    ai_feedback: Optional[str] = None
    user_answer: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Interview Schema
class InterviewBase(BaseModel):
    title: str
    job_title: str
    job_description: Optional[str] = None
    industry: Optional[str] = None
    difficulty_level: Optional[str] = Field(None, description="easy, medium, hard")
    interview_type: Optional[str] = Field(None, description="technical, behavioral, mixed")

class InterviewCreate(InterviewBase):
    pass

class InterviewUpdate(InterviewBase):
    status: Optional[str] = None

class Interview(InterviewBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    questions: List[InterviewQuestion] = []
    
    class Config:
        from_attributes = True

# Generation Request Schema
class GenerateQuestionsRequest(BaseModel):
    job_title: str
    job_description: Optional[str] = None
    industry: Optional[str] = None
    num_questions: int = Field(5, ge=1, le=20, description="Number of questions to generate")
    difficulty_level: str = Field("medium", description="easy, medium, hard")
    interview_type: str = Field("mixed", description="technical, behavioral, mixed")
    skills_required: Optional[List[str]] = None
    
# Generation Response Schema
class GenerateQuestionsResponse(BaseModel):
    interview_id: int
    title: str
    job_title: str
    questions: List[InterviewQuestion] 