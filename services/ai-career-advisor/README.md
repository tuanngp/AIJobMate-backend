# AI Career Advisor Service

Dịch vụ tư vấn nghề nghiệp AI cho nền tảng AI JobMate.

## Tính năng

- Phân tích hồ sơ người dùng và đề xuất hướng nghề nghiệp phù hợp
- Xác định khoảng cách kỹ năng và đề xuất các kỹ năng cần phát triển
- Tìm kiếm ngành nghề phù hợp dựa trên vector embedding
- Tạo kế hoạch phát triển nghề nghiệp cá nhân hóa

## Công nghệ

- **Framework**: FastAPI
- **Database**: PostgreSQL với SQLAlchemy ORM
- **Caching**: Redis
- **AI**: OpenAI GPT-4 API
- **Vector Database**: Pinecone
- **Containerization**: Docker

## Cài đặt

### Yêu cầu

- Python 3.9+
- Docker và Docker Compose
- PostgreSQL
- Redis

### Cài đặt môi trường phát triển

```bash
# Clone repository
git clone https://github.com/your-organization/ai-jobmate.git
cd ai-jobmate/backend/services/ai-career-advisor

# Tạo và kích hoạt môi trường ảo
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Tạo file .env từ .env.example
cp ../../.env.example .env
# Chỉnh sửa file .env với các thông tin cấu hình của bạn
```

### Chạy ứng dụng

```bash
# Chạy ứng dụng trong chế độ phát triển
uvicorn app.main:app --reload
```

## API Endpoints

### Xác thực

- `POST /api/v1/auth/register`: Đăng ký người dùng mới
- `POST /api/v1/auth/login`: Đăng nhập và lấy token
- `GET /api/v1/auth/me`: Lấy thông tin người dùng hiện tại

### Hồ sơ nghề nghiệp

- `POST /api/v1/career-profiles`: Tạo hồ sơ nghề nghiệp mới
- `GET /api/v1/career-profiles`: Lấy danh sách hồ sơ nghề nghiệp của người dùng
- `GET /api/v1/career-profiles/{profile_id}`: Lấy chi tiết hồ sơ nghề nghiệp
- `PUT /api/v1/career-profiles/{profile_id}`: Cập nhật hồ sơ nghề nghiệp
- `DELETE /api/v1/career-profiles/{profile_id}`: Xóa hồ sơ nghề nghiệp

### Tư vấn nghề nghiệp

- `POST /api/v1/career-advisor/analyze`: Phân tích hồ sơ và đưa ra tư vấn
- `GET /api/v1/career-advisor/recommendations`: Lấy các khuyến nghị nghề nghiệp
- `GET /api/v1/career-advisor/skill-gaps`: Phân tích khoảng cách kỹ năng

## Kiến trúc

```
app/
├── api/                  # API endpoints
│   ├── routes/           # API routes
│   └── deps.py           # API dependencies
├── core/                 # Core application code
│   ├── config.py         # Configuration settings
│   └── security.py       # Security utilities
├── db/                   # Database
│   ├── base.py           # Base model
│   └── session.py        # Database session
├── models/               # SQLAlchemy models
│   ├── user.py           # User model
│   └── career_profile.py # Career profile model
├── schemas/              # Pydantic schemas
│   ├── user.py           # User schemas
│   └── career_profile.py # Career profile schemas
├── services/             # Business logic
│   ├── openai_service.py # OpenAI integration
│   └── pinecone_service.py # Pinecone integration
└── main.py               # Application entry point
```

## Triển khai

Service này được thiết kế để triển khai trên AWS Lambda hoặc AWS ECS, tùy thuộc vào yêu cầu về thời gian phản hồi và tải.

## Giám sát

- Prometheus metrics được cung cấp tại endpoint `/metrics`
- Distributed tracing với AWS X-Ray
- Logging tập trung với AWS CloudWatch 