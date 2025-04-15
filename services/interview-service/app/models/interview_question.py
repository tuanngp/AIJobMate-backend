from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"))
    question = Column(Text)
    question_type = Column(String(50))  # technical, behavioral, situational
    difficulty = Column(String(20))  # easy, medium, hard
    category = Column(String(100), nullable=True)  # e.g., "programming", "database", "leadership"
    sample_answer = Column(Text, nullable=True)
    ai_feedback = Column(Text, nullable=True)
    user_answer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    interview = relationship("Interview", back_populates="questions") 