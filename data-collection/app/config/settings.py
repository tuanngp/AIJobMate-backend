from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn, field_validator

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Data Collection Service"

    # PostgreSQL for metadata and job tracking
    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_URI: PostgresDsn | None = None

    @field_validator("POSTGRES_URI", mode='before')
    @classmethod
    def assemble_postgres_uri(cls, v: str | None, values: Dict[str, Any]) -> str:
        if v:
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values["POSTGRES_USER"],
            password=values["POSTGRES_PASSWORD"],
            host=values["POSTGRES_HOST"],
            path=f"/{values['POSTGRES_DB']}"
        )

    # MongoDB for raw data storage
    MONGODB_HOST: str
    MONGODB_PORT: int = 27017
    MONGODB_USER: str
    MONGODB_PASSWORD: str
    MONGODB_DB: str
    MONGODB_URI: str | None = None

    @field_validator("MONGODB_URI", mode='before')
    @classmethod
    def assemble_mongo_uri(cls, v: str | None, values: Dict[str, Any]) -> str:
        if v:
            return v
        return (
            f"mongodb://{values['MONGODB_USER']}:{values['MONGODB_PASSWORD']}"
            f"@{values['MONGODB_HOST']}:{values['MONGODB_PORT']}/{values['MONGODB_DB']}"
        )

    # Redis for caching and task queues
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str
    REDIS_DB: int = 0
    REDIS_URI: RedisDsn | None = None

    @field_validator("REDIS_URI", mode='before')
    @classmethod
    def assemble_redis_uri(cls, v: str | None, values: Dict[str, Any]) -> str:
        if v:
            return v
        return RedisDsn.build(
            scheme="redis",
            host=values["REDIS_HOST"],
            port=values["REDIS_PORT"],
            password=values["REDIS_PASSWORD"],
            path=f"/{values['REDIS_DB']}"
        )

    # MinIO for object storage
    MINIO_HOST: str
    MINIO_PORT: int = 9000
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = True
    MINIO_BUCKET: str = "data-collection"

    # Elasticsearch for search and analytics
    ELASTICSEARCH_HOST: str
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_USER: str
    ELASTICSEARCH_PASSWORD: str
    ELASTICSEARCH_INDEX_PREFIX: str = "data_collection"

    # Data Collection Settings
    DATA_SOURCES: List[str] = [
        "linkedin",
        "indeed",
        "glassdoor",
        "monster",
        "dice",
        "stackoverflow",
        "github"
    ]
    
    MAX_CONCURRENT_TASKS: int = 10
    REQUEST_TIMEOUT: int = 30
    RETRY_COUNT: int = 3
    RETRY_DELAY: int = 5
    
    # Rate Limiting
    REQUESTS_PER_SECOND: float = 1.0
    REQUESTS_PER_MINUTE: int = 60
    REQUESTS_PER_HOUR: int = 1000

    # Data Validation
    MIN_TEXT_LENGTH: int = 50
    MAX_TEXT_LENGTH: int = 100000
    REQUIRED_FIELDS: List[str] = [
        "title",
        "description",
        "company",
        "location"
    ]
    
    # Data Processing
    BATCH_SIZE: int = 1000
    MAX_WORKERS: int = 4
    CHUNK_SIZE: int = 100
    USE_GPU: bool = False
    
    # Data Quality
    MIN_QUALITY_SCORE: float = 0.7
    DEDUPLICATION_THRESHOLD: float = 0.9
    TEXT_CLEANING_RULES: Dict[str, Any] = {
        "remove_html": True,
        "fix_unicode": True,
        "remove_accents": True,
        "normalize_whitespace": True
    }

    # Storage Settings
    DATA_DIR: str = "/app/data"
    RAW_DATA_DIR: str = "/app/data/raw"
    PROCESSED_DATA_DIR: str = "/app/data/processed"
    MODELS_DIR: str = "/app/models"
    CACHE_DIR: str = "/app/cache"
    
    # Cache Settings
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_MAX_ITEMS: int = 10000
    
    # Monitoring and Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_TELEMETRY: bool = True
    METRIC_COLLECTION_INTERVAL: int = 60  # seconds
    HEALTH_CHECK_INTERVAL: int = 30  # seconds

    # Pipeline Settings
    PIPELINE_SCHEDULE: Dict[str, str] = {
        "job_data": "0 */1 * * *",  # Every hour
        "company_data": "0 */6 * * *",  # Every 6 hours
        "market_trends": "0 0 * * *",  # Daily
        "skills_taxonomy": "0 0 * * 0"  # Weekly
    }
    
    PIPELINE_TIMEOUTS: Dict[str, int] = {
        "job_data": 3600,
        "company_data": 7200,
        "market_trends": 14400,
        "skills_taxonomy": 28800
    }

    # Feature Flags
    ENABLE_REAL_TIME_PROCESSING: bool = True
    ENABLE_ADVANCED_ANALYTICS: bool = True
    ENABLE_AUTO_SCALING: bool = True
    ENABLE_DATA_QUALITY_CHECKS: bool = True
    ENABLE_ANOMALY_DETECTION: bool = True

    # API Keys and External Services
    OPENAI_API_KEY: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    LINKEDIN_API_KEY: str
    INDEED_API_KEY: str
    GLASSDOOR_API_KEY: str

    # Security
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # Error Handling
    MAX_ERRORS_BEFORE_SHUTDOWN: int = 100
    ERROR_COOLDOWN_PERIOD: int = 300  # 5 minutes

    # Notification Settings
    ENABLE_NOTIFICATIONS: bool = True
    NOTIFICATION_CHANNELS: List[str] = ["email", "slack"]
    ALERT_THRESHOLDS: Dict[str, float] = {
        "error_rate": 0.1,
        "latency": 1000,
        "failure_rate": 0.05
    }

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()
