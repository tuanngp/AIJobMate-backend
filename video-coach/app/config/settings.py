from typing import List
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Video Interview Coach Service"

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
    MILVUS_COLLECTION: str = "video_embeddings"
    EMBEDDING_DIM: int = 512  # CLIP embedding dimension

    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = "ai-jobmate-video-storage"

    # OpenAI
    OPENAI_API_KEY: str
    ANALYSIS_MODEL: str = "gpt-4"
    CLIP_MODEL: str = "clip-vit-base-patch32"

    # Video Processing Settings
    MAX_VIDEO_LENGTH: int = 900  # 15 minutes in seconds
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500MB
    SUPPORTED_VIDEO_FORMATS: List[str] = ["mp4", "mov", "avi", "mkv"]
    
    # Video Analysis Settings
    FRAME_EXTRACTION_RATE: int = 1  # Extract 1 frame per second
    MIN_FACE_SIZE: int = 30  # Minimum face size in pixels
    FACE_DETECTION_CONFIDENCE: float = 0.5
    EMOTION_DETECTION_CONFIDENCE: float = 0.7
    
    # Analysis Features
    ANALYZE_FACIAL_EXPRESSIONS: bool = True
    ANALYZE_BODY_LANGUAGE: bool = True
    ANALYZE_EYE_CONTACT: bool = True
    ANALYZE_GESTURES: bool = True
    
    # Processing Paths
    UPLOAD_DIR: str = "/tmp/video-uploads"
    FRAMES_DIR: str = "/tmp/video-frames"
    
    # Cache settings
    CACHE_EXPIRE_TIME: int = 3600  # 1 hour
    
    # Security
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    JWT_SECRET_KEY: str = "your-secret-key"  # Change in production
    JWT_ALGORITHM: str = "HS256"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # Change in production

    # Performance Tuning
    BATCH_SIZE: int = 32  # Batch size for video frame processing
    NUM_WORKERS: int = 4  # Number of worker processes
    USE_GPU: bool = False  # Whether to use GPU for processing
    MEMORY_LIMIT: int = 8 * 1024 * 1024 * 1024  # 8GB memory limit

    class Config:
        case_sensitive = True
        env_file = ".env"

# Create settings instance
settings = Settings()
