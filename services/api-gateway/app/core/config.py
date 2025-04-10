import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    # API Gateway settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Service URLs
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    CAREER_ADVISOR_SERVICE_URL: str = "http://career-advisor-service:8002"
    FRONTEND_URL: str = "http://localhost:3000"

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
        "/api/v1/auth",
        "/api/v1/users",
        "/api/v1/rbac"
    ]
    
    CAREER_ADVISOR_PATHS: List[str] = [
        "/api/v1/career-profiles",
        "/api/v1/career-advisor",
        "/api/v1/cv"
    ]

    # Monitoring
    ENABLE_METRICS: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

# Initialize settings
settings = Settings()