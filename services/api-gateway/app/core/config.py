import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    # API Gateway settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Service URLs
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    CAREER_ADVISOR_SERVICE_URL: str = os.getenv("CAREER_ADVISOR_SERVICE_URL", "http://localhost:8002")
    INTERVIEW_SERVICE_URL: str = os.getenv("INTERVIEW_SERVICE_URL", "http://localhost:8003")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    @validator("ALLOWED_ORIGINS", pre=True)
    def validate_allowed_origins(cls, v):
        if isinstance(v, str):
            try:
                v = eval(v)
            except Exception:
                v = v.split(",")
        return v

    # Rate limiting
    RATE_LIMIT: int = 100
    RATE_LIMIT_PERIOD: int = 60  # seconds

    # Service paths
    AUTH_PATHS: List[str] = [
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/auth/logout",
        "/auth/verify",
        "/users/me",
        "/users",
        "/users/{user_id}",
        "/users/{user_id}/disable",
        "/users/{user_id}/enable",
        "/health"
    ]
    
    CAREER_ADVISOR_PATHS: List[str] = [
        # Base paths
        "/api/v1/users",
        "/api/v1/cv",
        "/api/v1/career-profiles",
        "/api/v1/career-advisor",
        # User endpoints
        "/api/v1/users/me",
        "/api/v1/users/{user_id}",
        # CV endpoints
        "/api/v1/cv/upload",
        "/api/v1/cv/list",
        "/api/v1/cv/{cv_id}",
        "/api/v1/cv/{cv_id}/analyze",
        # Career profile endpoints
        "/api/v1/career-profiles/",
        "/api/v1/career-profiles/{profile_id}",
        # Career advisor endpoints
        "/api/v1/career-advisor/analyze",
        "/api/v1/career-advisor/analyze/{task_id}",
        "/api/v1/career-advisor/recommendations",
        # Health check
        "health"
    ]

    INTERVIEW_PATHS: List[str] = [
        # Base paths
        "/api/v1/interviews",
        "/api/v1/interviews/{interview_id}",
        "/api/v1/interviews/{interview_id}/questions",
        "/api/v1/interviews/{interview_id}/questions/{question_id}",
        "/api/v1/interviews/{interview_id}/questions/{question_id}/answer",
        # Practice session paths
        "/api/v1/practice-sessions",
        "/api/v1/practice-sessions/{session_id}",
        "/api/v1/practice-sessions/{session_id}/answer",
        # Health check
        "/health"
    ]

    # Monitoring
    ENABLE_METRICS: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

# Initialize settings
settings = Settings()