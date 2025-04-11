# Chi Tiết Code Guide Phát Triển Service

## 1. Cấu Trúc Code Base

### 1.1 Models (app/api/models)

**career_profile.py**
```python
from sqlalchemy import Column, String, JSON, ARRAY, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.db.base_class import Base

class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    education = Column(JSON, nullable=True)
    experience = Column(JSON, nullable=True)
    skills = Column(ARRAY(String), nullable=True)
    interests = Column(ARRAY(String), nullable=True)
    vector_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**schemas.py**
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class Education(BaseModel):
    degree: str
    major: str
    school: str
    year: int

class Experience(BaseModel):
    title: str
    company: str
    duration: str
    description: str

class CareerProfileCreate(BaseModel):
    education: List[Education]
    experience: List[Experience]
    skills: List[str]
    interests: List[str]

class CareerProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    education: List[Education]
    experience: List[Experience]
    skills: List[str]
    interests: List[str]
    created_at: datetime
```

### 1.2 Services (app/services)

**ai_service.py**
```python
import httpx
from typing import Dict, Any
from app.core.config import settings

class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        
    async def analyze_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = self._create_analysis_prompt(profile_data)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": settings.MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            
            if response.status_code == 200:
                return self._parse_ai_response(response.json())
            else:
                raise Exception(f"AI API Error: {response.text}")
                
    def _create_analysis_prompt(self, profile_data: Dict[str, Any]) -> str:
        # Tạo prompt cho AI dựa trên profile data
        return f"""Analyze the following career profile and provide insights:
        Education: {profile_data['education']}
        Experience: {profile_data['experience']}
        Skills: {profile_data['skills']}
        Interests: {profile_data['interests']}
        """

    def _parse_ai_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        # Xử lý và format kết quả từ AI
        content = response['choices'][0]['message']['content']
        # Implement parsing logic
        return {"analysis": content}
```

**vector_service.py**
```python
import pinecone
from typing import List, Dict, Any
from app.core.config import settings

class VectorService:
    def __init__(self):
        pinecone.init(
            api_key=settings.PINECONE_API_KEY,
            environment=settings.PINECONE_ENV
        )
        self.index = pinecone.Index("career-profiles")
        
    async def store_profile_vector(self, profile_id: str, vector: List[float]) -> None:
        self.index.upsert([(profile_id, vector)])
        
    async def search_similar_profiles(
        self, 
        vector: List[float], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        results = self.index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True
        )
        return results['matches']
```

### 1.3 Controllers (app/api/controllers)

**career_controller.py**
```python
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.api.models.career_profile import CareerProfile
from app.services.ai_service import AIService
from app.services.vector_service import VectorService
from app.core.cache import RedisCache

class CareerController:
    def __init__(self):
        self.ai_service = AIService()
        self.vector_service = VectorService()
        self.cache = RedisCache()
        
    async def analyze_profile(
        self, 
        db: Session, 
        profile_data: Dict[str, Any], 
        user_id: UUID
    ) -> Dict[str, Any]:
        # Check cache
        cache_key = f"analysis:{user_id}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
            
        # Create profile in DB
        profile = CareerProfile(
            user_id=user_id,
            education=profile_data['education'],
            experience=profile_data['experience'],
            skills=profile_data['skills'],
            interests=profile_data['interests']
        )
        db.add(profile)
        db.commit()
        
        # Get AI analysis
        analysis = await self.ai_service.analyze_profile(profile_data)
        
        # Store in cache
        await self.cache.set(
            cache_key,
            analysis,
            expire=3600  # 1 hour
        )
        
        return analysis
```

### 1.4 Routes (app/api/routes)

**career.py**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.api.models.schemas import CareerProfileCreate, CareerProfileResponse
from app.api.controllers.career_controller import CareerController
from app.core.deps import get_db, get_current_user
from app.core.logger import logger

router = APIRouter()
controller = CareerController()

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_career_profile(
    profile: CareerProfileCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Analyze career profile and provide recommendations"""
    try:
        result = await controller.analyze_profile(
            db,
            profile.dict(),
            current_user.id
        )
        return result
    except Exception as e:
        logger.error(f"Error analyzing profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during profile analysis"
        )
```

## 2. Phát Triển Theo Từng Bước

### Bước 1: Setup Database và Models

1. Tạo migrations:
```bash
# Tạo migration
alembic revision --autogenerate -m "create_career_profiles"

# Apply migration
alembic upgrade head
```

2. Kiểm tra kết nối database:
```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test connection
def test_db():
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
```

### Bước 2: Implement Services

1. Setup OpenRouter API:
```python
# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    MODEL_NAME: str = "gpt-3.5-turbo"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

2. Setup Pinecone:
```python
# Khởi tạo Pinecone index
pinecone.create_index(
    name="career-profiles",
    dimension=1536,  # GPT embedding dimension
    metric="cosine"
)
```

### Bước 3: Implement Business Logic

1. Error handling:
```python
# app/core/exceptions.py
class AIServiceError(Exception):
    pass

class VectorServiceError(Exception):
    pass

# Trong controller
try:
    analysis = await self.ai_service.analyze_profile(profile_data)
except Exception as e:
    raise AIServiceError(f"AI analysis failed: {str(e)}")
```

2. Logging:
```python
# app/core/logger.py
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
```

### Bước 4: Testing

1. Unit tests:
```python
# tests/test_ai_service.py
import pytest
from app.services.ai_service import AIService

@pytest.mark.asyncio
async def test_analyze_profile():
    service = AIService()
    profile_data = {
        "education": [...],
        "experience": [...],
        "skills": [...],
        "interests": [...]
    }
    
    result = await service.analyze_profile(profile_data)
    assert "analysis" in result
```

2. Integration tests:
```python
# tests/test_career_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_analyze_endpoint():
    response = client.post(
        "/career/analyze",
        json={
            "education": [...],
            "experience": [...],
            "skills": [...],
            "interests": [...]
        }
    )
    assert response.status_code == 200
    assert "analysis" in response.json()
```

### Bước 5: Monitoring và Logging

1. Setup metrics:
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram

request_count = Counter(
    'career_advisor_requests_total',
    'Total requests to career advisor service'
)

analysis_duration = Histogram(
    'career_advisor_analysis_duration_seconds',
    'Time spent processing career analysis'
)
```

2. Implement middleware:
```python
# app/core/middleware.py
import time
from fastapi import Request
from app.core.metrics import request_count, analysis_duration

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    duration = time.time() - start_time
    request_count.inc()
    analysis_duration.observe(duration)
    
    return response
```

### Bước 6: Documentation

1. API documentation:
```python
@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_career_profile(
    profile: CareerProfileCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Analyze a user's career profile and provide recommendations.
    
    Parameters:
    - profile: Career profile information including education, experience, etc.
    
    Returns:
    - Analysis results including strengths, suggestions, and market insights
    
    Raises:
    - 401: Unauthorized
    - 500: Internal server error
    """
```

## 3. Deployment Checklist

1. Environment validation
2. Database migrations
3. Service dependencies
4. Security checks
5. Performance testing
6. Monitoring setup
7. Backup procedures

## 4. Maintenance Guidelines

1. Regular updates
2. Performance monitoring
3. Error tracking
4. Data backup
5. Security patches

## 5. Troubleshooting Guide

1. Database connection issues
2. AI service errors
3. Vector search problems
4. Cache inconsistencies
5. Performance bottlenecks