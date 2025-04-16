
from functools import lru_cache
import os
from typing import Dict, List, Tuple
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    # API Gateway settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
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
    SERVICE_ROUTES: Dict[str, Tuple[str, List[str]]] = {
        "auth": (AUTH_SERVICE_URL, [
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
        ]),
        "career_advisor": (CAREER_ADVISOR_SERVICE_URL, [
            "/users",
            "/cv",
            "/career-profiles",
            "/career-advisor", 
            "/users/me",
            "/users/{user_id}",
            "/cv/upload",
            "/cv/list",
            "/cv/{cv_id}",
            "/cv/{cv_id}/analyze",
            "/career-profiles/",
            "/career-profiles/{profile_id}",
            "/career-advisor/analyze",
            "/career-advisor/analyze/{task_id}",
            "/career-advisor/recommendations",
            "/health"
        ]),
        "interview": (INTERVIEW_SERVICE_URL, [
            "/interviews",
            "/interviews/{interview_id}",
            "/interviews/{interview_id}/questions",
            "/interviews/{interview_id}/questions/{question_id}",
            "/interviews/{interview_id}/questions/{question_id}/answer",
            "/practice-sessions",
            "/practice-sessions/{session_id}",
            "/practice-sessions/{session_id}/answer",
            "/health"
        ]),
    }
    
    PUBLIC_PATHS: List[str] = [
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/health"
    ]
    
    NO_PREFIX_PATHS: List[str] = [
        "/health"
    ]

    @property
    def route_mapping(self) -> Dict[str, str]:
        """
        Builds a comprehensive mapping of all routes to their target services,
        automatically applying API_PREFIX where needed.
        """
        mapping = {}
        
        for service_name, (service_url, paths) in self.SERVICE_ROUTES.items():
            for path in paths:
                if path in self.NO_PREFIX_PATHS:
                    mapping[path] = service_url
                else:
                    # Remove leading slash if API_PREFIX already has it
                    clean_path = path[1:] if path.startswith("/") and self.API_PREFIX.endswith("/") else path
                    if not clean_path.startswith("/") and not self.API_PREFIX.endswith("/"):
                        clean_path = "/" + clean_path
                        
                    prefixed_path = f"{self.API_PREFIX}{clean_path}"
                    mapping[prefixed_path] = service_url
        
        return mapping

    # Monitoring
    ENABLE_METRICS: bool = True

    class Config:
        case_sensitive = True
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Create and cache settings instance."""
    return Settings()

# Initialize settings
settings = Settings()