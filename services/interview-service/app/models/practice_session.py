from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    total_questions = Column(Integer, nullable=False)
    completed_questions = Column(Integer, default=0)
    average_score = Column(Numeric(4,2), nullable=True)
    status = Column(String(20), default="in_progress")
    settings = Column(JSON, nullable=True)

    # Relationships
    interview = relationship("Interview", back_populates="sessions")
    recordings = relationship("AnswerRecording", back_populates="session", cascade="all, delete-orphan")

class AnswerRecording(Base):
    __tablename__ = "answer_recordings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("practice_sessions.id"))
    question_id = Column(Integer, ForeignKey("interview_questions.id"))
    audio_url = Column(String)
    transcription = Column(String)
    feedback = Column(JSON)
    score = Column(Numeric(4,2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("PracticeSession", back_populates="recordings")
    question = relationship("InterviewQuestion", back_populates="recordings")