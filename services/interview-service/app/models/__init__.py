# Import all models here for SQLAlchemy discovery
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.practice_session import PracticeSession
# User model is not imported to avoid cross-service dependency 