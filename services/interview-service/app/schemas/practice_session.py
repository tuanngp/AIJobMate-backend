from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class SessionSettings(BaseModel):
    language: str = "en"
    use_video: bool = False
    time_limit_per_question: Optional[int] = None

class PracticeSessionCreate(BaseModel):
    interview_id: int
    settings: Optional[SessionSettings] = None

class AnswerRecordingCreate(BaseModel):
    question_id: int
    audio_url: str
    transcription: str

class AnswerRecordingResponse(BaseModel):
    id: int
    question_id: int
    audio_url: str
    transcription: str
    feedback: dict
    score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class PracticeSessionResponse(BaseModel):
    id: int
    interview_id: int
    start_time: datetime
    end_time: Optional[datetime]
    total_questions: int
    completed_questions: int
    average_score: Optional[float]
    status: str
    settings: Optional[SessionSettings]
    recordings: List[AnswerRecordingResponse] = []

    class Config:
        from_attributes = True