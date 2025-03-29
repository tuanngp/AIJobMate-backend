import os
import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import PostgresDsn, validator, AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API and Application Config
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Career Advisor"
    VERSION: str = "1.0.0"
    
    # Security configurations
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS configuration
    CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Database configuration
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "123")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ai_career_advisor")
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        postgres_dsn = PostgresDsn.build(
            scheme="postgresql",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"{values.get('POSTGRES_DB') or ''}",
        )
        return str(postgres_dsn)
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    
    # OpenAI/OpenRouter configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    SITE_URL: str = os.getenv("SITE_URL", "http://localhost:3000")
    SITE_NAME: str = os.getenv("SITE_NAME", "AI Career Advisor")
    AI_MODEL: str = os.getenv("AI_MODEL", "deepseek/deepseek-r1:free")
    
    # Pinecone configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "")
    PINECONE_INDEX: str = os.getenv("PINECONE_INDEX", "career-advisor")
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
