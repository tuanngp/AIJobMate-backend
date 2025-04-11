# Hướng Dẫn Phát Triển Career Advisor Service

## 1. Thiết Lập Ban Đầu

### 1.1 Cấu Trúc Project
```bash
# 1. Tạo cấu trúc thư mục cơ bản
mkdir -p services/career-advisor-service
cd services/career-advisor-service

# 2. Khởi tạo Python project
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
.\venv\Scripts\activate  # Windows

# 3. Cài đặt dependencies
pip install fastapi[all] sqlalchemy psycopg2-binary redis pinecone-client python-jose[cryptography] python-dotenv pytest
pip freeze > requirements.txt
```

### 1.2 Cấu Trúc Thư Mục
```
career-advisor-service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── career.py      # API endpoints
│   │   │   └── health.py      # Health check
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── profile.py     # Career profile model
│   │   │   └── analysis.py    # Analysis model
│   │   └── controllers/
│   │       └── career.py      # Business logic
│   ├── core/
│   │   ├── config.py          # Configuration
│   │   └── security.py        # Security utils
│   ├── services/
│   │   ├── ai_service.py      # OpenRouter integration
│   │   ├── vector_service.py  # Pinecone integration
│   │   └── cache_service.py   # Redis cache
│   └── main.py               # FastAPI application
├── tests/
├── alembic/                  # Database migrations
├── requirements.txt
└── Dockerfile
```

## 2. Quy Trình Phát Triển

```mermaid
graph TD
    A[1. Cấu trúc Ban đầu] --> B[2. Database Setup]
    B --> C[3. Models & Schemas]
    C --> D[4. Services Layer]
    D --> E[5. API Routes]
    E --> F[6. Integration Tests]

    subgraph "1. Cấu trúc Ban đầu"
        A1[Tạo Project Structure]
        A2[Setup Dependencies]
        A3[Config Files]
    end

    subgraph "2. Database Setup"
        B1[PostgreSQL Schema]
        B2[Redis Config]
        B3[Pinecone Setup]
    end
```

## 3. Các Bước Triển Khai Chi Tiết

### 3.1 Setup Database

**a. Tạo PostgreSQL Database**
```sql
-- Kết nối vào PostgreSQL
psql -U postgres

-- Tạo database
CREATE DATABASE career_advisor_service;

-- Tạo extensions cần thiết
\c career_advisor_service
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**b. Setup Alembic Migrations**
```bash
# Khởi tạo Alembic
alembic init alembic

# Tạo migration đầu tiên
alembic revision --autogenerate -m "initial"

# Chạy migration
alembic upgrade head
```

### 3.2 Cấu hình Environment

Tạo file `.env`:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/career_advisor_service

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_password

# Pinecone
PINECONE_API_KEY=your_key
PINECONE_ENV=your_env

# OpenRouter (AI)
OPENROUTER_API_KEY=your_key
MODEL_NAME=gpt-3.5-turbo

# Service Config
SERVICE_NAME=career-advisor-service
SERVICE_VERSION=0.1.0
```

### 3.3 Thiết lập FastAPI Application

**a. Main Application (app/main.py)**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import career, health

app = FastAPI(
    title="Career Advisor Service",
    description="AI-powered career guidance and job recommendations",
    version="0.1.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(career.router, prefix="/career", tags=["career"])
app.include_router(health.router, prefix="/health", tags=["health"])
```

### 3.4 Development Workflow

**a. Khởi động Services**
```bash
# Start Database & Redis
docker-compose up -d

# Start FastAPI
uvicorn app.main:app --reload --port 8000
```

**b. Testing**
```bash
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# Kiểm tra API Documentation
open http://localhost:8000/docs
```

## 4. Công Cụ và Commands Hữu ích

### 4.1 Database Commands
```bash
# Generate migration
alembic revision --autogenerate -m "add_new_table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### 4.2 API Testing
```bash
# Test Profile Analysis
curl -X POST http://localhost:8000/career/analyze \
  -H "Content-Type: application/json" \
  -d @test_payload.json

# Health Check
curl http://localhost:8000/health
```

### 4.3 Code Generation
```bash
# Generate FastAPI route template
fastapi-codegen -i openapi.json -o app/api/routes
```

## 5. Best Practices & Lưu ý

### 5.1 Error Handling
- Implement global exception handler
- Sử dụng custom exceptions
- Log errors với đầy đủ context

### 5.2 Performance
- Cache kết quả AI calls
- Sử dụng async/await cho I/O operations
- Implement connection pooling

### 5.3 Security
- Rate limiting cho tất cả endpoints
- Input validation
- Implement circuit breakers

### 5.4 Monitoring
- Request/Response logging
- Performance metrics
- AI model monitoring
- Cache hit/miss ratio

## 6. CI/CD Setup

### 6.1 GitHub Actions workflow
```yaml
name: Career Advisor CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest
```

## 7. Deployment

### 7.1 Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 Docker Compose
```yaml
version: '3.8'
services:
  career-advisor:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: career_advisor_service
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## 8. Tài Liệu Tham Khảo

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pinecone Documentation](https://www.pinecone.io/docs/)
- [Redis Documentation](https://redis.io/documentation)