from typing import List, Dict
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Job Matching Service"

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
    MILVUS_COLLECTION: str = "job_embeddings"
    EMBEDDING_DIM: int = 768  # BERT embedding dimension

    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "ai-jobmate-job-data"

    # OpenAI
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    ANALYSIS_MODEL: str = "gpt-4"

    # ML Model Settings
    MODEL_PATHS: Dict[str, str] = {
        "skill_extractor": "/app/models/skill_extractor",
        "job_classifier": "/app/models/job_classifier",
        "salary_predictor": "/app/models/salary_predictor"
    }
    
    # Skill Taxonomy Settings
    SKILLS_DATA_PATH: str = "/app/data/skills/taxonomy.json"
    SKILLS_UPDATE_INTERVAL: int = 24 * 60 * 60  # 24 hours
    MIN_SKILL_CONFIDENCE: float = 0.7
    
    # Job Matching Settings
    MATCH_THRESHOLD: float = 0.75
    MAX_MATCHES: int = 20
    SKILL_WEIGHT: float = 0.6
    EXPERIENCE_WEIGHT: float = 0.2
    LOCATION_WEIGHT: float = 0.2
    
    # Job Search Settings
    SUPPORTED_JOB_BOARDS: List[str] = [
        "linkedin",
        "indeed",
        "glassdoor"
    ]
    SEARCH_DELAY: int = 1  # Delay between requests in seconds
    MAX_JOBS_PER_QUERY: int = 100
    JOB_CACHE_TTL: int = 60 * 60  # 1 hour
    
    # Scraping Settings
    USER_AGENT: str = "AI-JobMate Bot/1.0"
    SCRAPE_TIMEOUT: int = 30  # seconds
    MAX_RETRIES: int = 3
    CHROME_DRIVER_PATH: str = "/usr/bin/chromedriver"
    
    # Salary Prediction Settings
    SALARY_DATA_PATH: str = "/app/data/salary/dataset.csv"
    SALARY_MODEL_VERSION: str = "v1.0"
    PREDICTION_CACHE_TTL: int = 24 * 60 * 60  # 24 hours
    
    # Data Collection Settings
    DATA_DIR: str = "/app/data"
    COLLECTION_INTERVAL: int = 60 * 60  # 1 hour
    MIN_JOBS_PER_COLLECTION: int = 1000
    
    # Cache settings
    CACHE_EXPIRE_TIME: int = 3600  # 1 hour
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_SECRET_KEY: str = "your-secret-key"  # Change in production
    JWT_ALGORITHM: str = "HS256"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # Change in production

    # Performance Tuning
    BATCH_SIZE: int = 32
    NUM_WORKERS: int = 4
    USE_GPU: bool = False
    EMBEDDING_BATCH_SIZE: int = 128
    MAX_CONCURRENT_REQUESTS: int = 10

    # Feature Flags
    ENABLE_REAL_TIME_UPDATES: bool = True
    ENABLE_SMART_MATCHING: bool = True
    ENABLE_SALARY_PREDICTIONS: bool = True
    ENABLE_SKILL_SUGGESTIONS: bool = True
    ENABLE_LOCATION_BASED_SEARCH: bool = True
    ENABLE_REMOTE_WORK_FILTER: bool = True

    # Monitoring and Logging
    ENABLE_TELEMETRY: bool = True
    LOG_LEVEL: str = "INFO"
    METRIC_COLLECTION_INTERVAL: int = 60  # seconds

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()
