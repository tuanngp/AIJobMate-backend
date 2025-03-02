from typing import List
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Career Advisor Service"

    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_URI: PostgresDsn | None = None

    @property
    def get_postgres_uri(self) -> str:
        """Get PostgreSQL URI"""
        if not self.POSTGRES_URI:
            self.POSTGRES_URI = PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                path=f"/{self.POSTGRES_DB}",
            )
        return str(self.POSTGRES_URI)

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_URI: RedisDsn | None = None

    @property
    def get_redis_uri(self) -> str:
        """Get Redis URI"""
        if not self.REDIS_URI:
            self.REDIS_URI = RedisDsn.build(
                scheme="redis",
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
            )
        return str(self.REDIS_URI)

    # Milvus
    MILVUS_HOST: str
    MILVUS_PORT: int = 19530

    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "ai-jobmate-cv-storage"

    # OpenAI
    OPENAI_API_KEY: str
    CV_ANALYSIS_MODEL: str = "gpt-4"
    CAREER_ADVICE_MODEL: str = "gpt-4"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"

    # Cache settings
    CACHE_EXPIRE_TIME: int = 3600  # 1 hour
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_SECRET_KEY: str = "your-secret-key"  # Change in production
    JWT_ALGORITHM: str = "HS256"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # Change in production

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()
