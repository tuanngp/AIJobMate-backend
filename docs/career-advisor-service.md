# AI Career Advisor Service Documentation

## 1. Tổng quan / Overview

### Mục đích / Purpose
AI Career Advisor Service là microservice chính trong hệ thống AI JobMate, cung cấp các chức năng tư vấn nghề nghiệp thông minh sử dụng AI. Service này xử lý việc phân tích hồ sơ, đề xuất nghề nghiệp, và cung cấp thông tin thị trường việc làm.

### Công nghệ sử dụng / Technologies
- Framework: FastAPI
- Database: PostgreSQL
- Cache: Redis
- Vector Database: Pinecone
- AI Model: OpenRouter (GPT)
- Message Queue: Redis PubSub

## 2. Quy trình xử lý / Processing Flow

### Phân tích hồ sơ / Profile Analysis Flow
1. Client gửi thông tin hồ sơ
2. Validate và chuẩn hóa dữ liệu
3. Vector embedding thông tin
4. Lưu vào Pinecone
5. Gọi OpenRouter API để phân tích
6. Cache kết quả trong Redis
7. Trả về phân tích chi tiết

### Đề xuất việc làm / Job Recommendation Flow
1. Nhận yêu cầu đề xuất
2. Lấy vector profile từ Pinecone
3. Tìm kiếm các công việc phù hợp
4. Tính toán mức độ phù hợp
5. Cache kết quả
6. Trả về danh sách đề xuất

### Feedback Loop
1. Nhận feedback từ user
2. Cập nhật trọng số đề xuất
3. Retrain local model (nếu cần)
4. Lưu metrics

## 3. API Endpoints

### POST /career/analyze
Phân tích hồ sơ nghề nghiệp

**Request Schema:**
```json
{
  "profile": {
    "education": [
      {
        "degree": "string",
        "major": "string",
        "school": "string",
        "year": "number"
      }
    ],
    "experience": [
      {
        "title": "string",
        "company": "string",
        "duration": "string",
        "description": "string"
      }
    ],
    "skills": ["string"],
    "interests": ["string"]
  }
}
```

**Response Schema:**
```json
{
  "analysis": {
    "strengths": ["string"],
    "weaknesses": ["string"],
    "suggested_roles": [
      {
        "role": "string",
        "confidence": "number",
        "reasons": ["string"]
      }
    ],
    "skill_gaps": ["string"],
    "market_insights": {
      "demand_level": "string",
      "salary_range": {
        "min": "number",
        "max": "number",
        "currency": "string"
      }
    }
  }
}
```

### GET /career/recommendations
Lấy đề xuất việc làm phù hợp

**Query Parameters:**
- profile_id: string (required)
- limit: number (optional, default: 10)
- offset: number (optional, default: 0)

**Response Schema:**
```json
{
  "recommendations": [
    {
      "job_id": "string",
      "title": "string",
      "company": "string",
      "match_score": "number",
      "salary_range": {
        "min": "number",
        "max": "number",
        "currency": "string"
      },
      "requirements": ["string"],
      "match_reasons": ["string"]
    }
  ],
  "total": "number",
  "page": "number",
  "has_more": "boolean"
}
```

### POST /career/feedback
Gửi feedback về đề xuất

**Request Schema:**
```json
{
  "recommendation_id": "string",
  "rating": "number",
  "feedback_type": "string",
  "comments": "string?",
  "applied": "boolean"
}
```

**Response Schema:**
```json
{
  "status": "success",
  "feedback_id": "string",
  "updated_score": "number?"
}
```

## 4. Database Schema

### CareerProfiles Table
```sql
CREATE TABLE career_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    education JSONB,
    experience JSONB,
    skills TEXT[],
    interests TEXT[],
    vector_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### CareerAnalysis Table
```sql
CREATE TABLE career_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES career_profiles(id),
    analysis_data JSONB NOT NULL,
    model_version VARCHAR(50),
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Recommendations Table
```sql
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES career_profiles(id),
    job_data JSONB NOT NULL,
    match_score FLOAT,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Feedback Table
```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendations(id),
    user_id UUID NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_type VARCHAR(50),
    comments TEXT,
    applied BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## 5. Service Dependencies

### Required Services
- PostgreSQL Database (career_advisor_service database)
- Redis Cache
- Pinecone Vector Database

### External Dependencies
- OpenRouter API (GPT)
- Job Market Data API (optional)

## 6. API Integration Requirements

### Headers
```
Content-Type: application/json
Authorization: Bearer <access_token>
X-Request-ID: <unique_request_id>
```

### Validation Rules
- Các trường bắt buộc phải có đầy đủ
- Định dạng ngày tháng: ISO 8601
- Rating: 1-5
- Vector dimensions: 1536 (GPT)

### Status Codes
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Validation Error
- 429: Too Many Requests
- 500: Internal Server Error

### Error Response Format
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {},
    "request_id": "string"
  }
}
```

### Rate Limiting
- 50 requests/minute cho phân tích hồ sơ
- 200 requests/minute cho đề xuất việc làm
- 500 requests/minute cho feedback

## 7. Service Communication

### Communication Patterns
- REST APIs (Synchronous)
- Redis PubSub (Asynchronous)
- Vector Search (Pinecone)

### Message Queue Requirements
- Profile Analysis Queue
- Recommendation Update Queue
- Feedback Processing Queue

### Retry Policy
- Maximum 5 retries cho AI calls
- Exponential backoff: 1s, 2s, 4s, 8s, 16s
- Jitter: 0-1000ms

### Timeout Configuration
- API endpoints: 30 seconds
- AI model calls: 45 seconds
- Vector search: 10 seconds
- Database queries: 5 seconds

### Circuit Breaker
- Threshold: 40% failure rate
- Reset timeout: 60 seconds
- Half-open state: Allow 5 requests

## 8. Monitoring & Logging

### Health Check Endpoint
GET /health
```json
{
  "status": "healthy",
  "version": "string",
  "dependencies": {
    "database": "connected",
    "redis": "connected",
    "pinecone": "connected",
    "openrouter": "operational"
  },
  "metrics": {
    "request_count": "number",
    "error_rate": "number",
    "average_latency": "number"
  },
  "timestamp": "datetime"
}
```

### Metrics
- API latency và success rate
- AI model performance metrics
- Vector search quality metrics
- Cache hit/miss ratio
- Queue length và processing time
- Error rates by category

### Logging
- Request/Response logs
- AI model inputs/outputs
- Vector search queries
- Performance bottlenecks
- Error stacks
- User feedback data

### Alert Rules
- Error rate > 10%
- Latency > 5s
- Queue length > 1000
- Cache miss rate > 40%
- AI model timeout > 5%