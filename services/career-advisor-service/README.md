# AI Career Advisor Service 🎯

## Giới thiệu

AI Career Advisor là core service của hệ thống AI JobMate, cung cấp các tính năng tư vấn nghề nghiệp thông minh:
- Phân tích hồ sơ nghề nghiệp
- Gợi ý nghề nghiệp phù hợp
- Đánh giá kỹ năng
- Lộ trình phát triển sự nghiệp
- Phân tích xu hướng thị trường

## Tech Stack

- FastAPI
- PostgreSQL
- Redis
- OpenRouter (GPT-4)
- Pinecone (Vector DB)
- SQLAlchemy
- Pydantic

## Cấu trúc Project

```
career-advisor-service/
├── src/
│   ├── api/           # API endpoints
│   ├── core/          # Core configurations
│   ├── models/        # Database models
│   ├── schemas/       # Data schemas
│   ├── services/      # Business logic
│   │   ├── ai/       # AI integrations
│   │   ├── career/   # Career analysis
│   │   └── skills/   # Skills assessment
│   └── utils/         # Utility functions
├── tests/
├── Dockerfile
└── requirements.txt
```

## AI Components

### 1. Profile Analysis
- Sử dụng GPT-4 để phân tích CV
- Trích xuất kỹ năng và kinh nghiệm
- Đánh giá điểm mạnh và điểm yếu

### 2. Career Matching
- Vector embedding cho job descriptions
- Similarity search với Pinecone
- Ranking và scoring các công việc phù hợp

### 3. Skills Assessment
- Đánh giá mức độ thành thạo
- Gap analysis
- Gợi ý học tập và phát triển

## API Endpoints

### Profile Analysis
- `POST /analyze/cv`
- `GET /analyze/results/{analysis_id}`
- `POST /analyze/feedback`

### Career Recommendations
- `GET /careers/recommendations`
- `GET /careers/trending`
- `GET /careers/skills/{career_id}`

### Skills Assessment
- `POST /skills/assess`
- `GET /skills/gap-analysis`
- `GET /skills/learning-path`

## Data Models

### Profile
```python
class Profile(BaseModel):
    id: UUID
    user_id: UUID
    education: List[Education]
    experience: List[Experience]
    skills: List[Skill]
    career_goals: List[str]
    created_at: datetime
    updated_at: datetime
```

### Career Analysis
```python
class CareerAnalysis(BaseModel):
    id: UUID
    profile_id: UUID
    recommendations: List[CareerRecommendation]
    skill_gaps: List[SkillGap]
    market_trends: List[MarketTrend]
    created_at: datetime
```

## Environment Variables

```env
# Database
POSTGRES_SERVER=postgres-career
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=career_advisor_service

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# AI Services
OPENROUTER_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_ENVIRONMENT=your_env
PINECONE_INDEX=your_index
```

## Caching Strategy

1. **Redis Caching**
   - Career recommendations: 24 giờ
   - Market trends: 12 giờ
   - Skill assessments: 48 giờ

2. **Cache Invalidation**
   - Tự động khi có updates
   - Manual flush qua API
   - Scheduled cleanup

## AI Processing Pipeline

1. Data Preprocessing
   - CV parsing
   - Text normalization
   - Entity extraction

2. AI Analysis
   - GPT-4 processing
   - Vector embeddings
   - Similarity matching

3. Post-processing
   - Result ranking
   - Confidence scoring
   - Recommendation filtering

## Development

1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

2. Setup vector database:
```bash
python scripts/setup_pinecone.py
```

3. Start development server:
```bash
uvicorn main:app --reload --port 8002
```

## Testing

```bash
# Unit tests
pytest

# AI integration tests
pytest tests/ai/

# Performance tests
pytest tests/performance/
```

## Monitoring

- AI performance metrics
- API latency
- Cache hit rates
- Vector DB metrics
- Model processing times

## Error Handling

Specific error codes:
- `422`: Invalid input format
- `429`: Rate limit exceeded
- `502`: AI service unavailable
- `504`: Processing timeout

## Performance Optimization

1. **Batch Processing**
   - Bulk analysis queue
   - Parallel processing
   - Background tasks

2. **Caching**
   - Result caching
   - Embedding caching
   - Frequent queries

3. **Database**
   - Index optimization
   - Query optimization
   - Connection pooling

## Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Update tests
5. Tạo Pull Request

### AI Development Guidelines
- Test accuracy metrics
- Bias testing
- Performance benchmarks
- Model versioning
- Data privacy compliance