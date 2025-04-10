# Hướng dẫn chạy thử AI Career Advisor Service

Đây là hướng dẫn chi tiết để cài đặt và chạy thử AI Career Advisor Service.

## 1. Yêu cầu môi trường

- Python 3.9+ 
- PostgreSQL
- Redis (tùy chọn, có thể comment ra trong code khi thử nghiệm)
- Tài khoản OpenAI API
- Tài khoản Pinecone (tùy chọn, có thể thay thế bằng mock data khi thử nghiệm)

## 2. Cài đặt

### 2.1. Cài đặt môi trường ảo

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2.2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2.3. Thiết lập database

```bash
# Khởi tạo database PostgreSQL
# Tạo database 'career_advisor_service'

# Chạy migration
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 2.4. Thiết lập môi trường

```bash
# Tạo file .env từ .env.sample
cp .env.sample .env

# Chỉnh sửa .env với các thông tin cần thiết
# - OPENAI_API_KEY: API key của OpenAI
# - PINECONE_API_KEY: API key của Pinecone (tùy chọn)
# - PINECONE_ENVIRONMENT: Environment của Pinecone (tùy chọn)
```

## 3. Chạy ứng dụng

```bash
# Chạy ứng dụng trong chế độ phát triển
uvicorn app.main:app --reload
```

Ứng dụng sẽ chạy tại http://localhost:8000

## 4. API Testing với Swagger UI

Truy cập Swagger UI tại http://localhost:8000/docs để thử nghiệm các API.

### 4.1. Đăng ký người dùng mới

```
POST /api/v1/auth/register
```

Payload:
```json
{
  "email": "test@example.com",
  "password": "password123",
  "full_name": "Test User"
}
```

### 4.2. Đăng nhập

```
POST /api/v1/auth/login
```

Form data:
- username: test@example.com
- password: password123

Bạn sẽ nhận được access token dùng cho các API khác.

### 4.3. Cập nhật thông tin profile

```
PUT /api/v1/users/me
```

Payload:
```json
{
  "skills": [
    "Python", 
    "FastAPI", 
    "SQL", 
    "Data Analysis", 
    "Machine Learning"
  ],
  "experiences": [
    {
      "title": "Data Analyst",
      "company": "Example Corp",
      "years": 2,
      "description": "Phân tích dữ liệu và tạo báo cáo."
    }
  ],
  "education": [
    {
      "degree": "Bachelor",
      "major": "Computer Science",
      "school": "Example University",
      "year": 2020
    }
  ],
  "career_goals": [
    "Trở thành Data Scientist",
    "Học thêm về AI và ML"
  ],
  "preferred_industries": [
    "Technology", 
    "Finance"
  ]
}
```

### 4.4. Tạo hồ sơ nghề nghiệp

```
POST /api/v1/career-profiles
```

Payload:
```json
{
  "title": "Hồ sơ nghề nghiệp 2023",
  "description": "Hồ sơ nghề nghiệp của tôi cho năm 2023"
}
```

### 4.5. Phân tích hồ sơ nghề nghiệp

```
POST /api/v1/career-advisor/analyze
```

Payload:
```json
{
  "profile_id": "id_của_hồ_sơ_vừa_tạo",
  "skills": [
    "Python", 
    "FastAPI", 
    "SQL", 
    "Data Analysis", 
    "Machine Learning"
  ],
  "experiences": [
    {
      "title": "Data Analyst",
      "company": "Example Corp",
      "years": 2,
      "description": "Phân tích dữ liệu và tạo báo cáo."
    }
  ],
  "education": [
    {
      "degree": "Bachelor",
      "major": "Computer Science",
      "school": "Example University",
      "year": 2020
    }
  ],
  "career_goals": [
    "Trở thành Data Scientist",
    "Học thêm về AI và ML"
  ],
  "preferred_industries": [
    "Technology", 
    "Finance"
  ]
}
```

### 4.6. Lấy gợi ý hướng nghề nghiệp

```
GET /api/v1/career-advisor/recommendations
```

### 4.7. Phân tích khoảng cách kỹ năng

```
GET /api/v1/career-advisor/skill-gaps?target_career=Data%20Scientist&experience_level=mid
```

## 5. Lưu ý quan trọng

1. Service này cần có kết nối internet để gọi APIs của OpenAI và Pinecone.
2. Nếu muốn chạy thử mà không cần Pinecone, bạn có thể sửa đổi hàm search_career_pathways trong file app/services/pinecone_service.py để trả về dữ liệu giả lập.
3. Đảm bảo rằng API keys của OpenAI có đủ credit để sử dụng.

## 6. Khắc phục sự cố

1. Lỗi kết nối database:
   - Kiểm tra PostgreSQL đã chạy chưa
   - Kiểm tra thông tin kết nối trong file .env

2. Lỗi OpenAI API:
   - Kiểm tra API key có hợp lệ không
   - Kiểm tra có đủ credit không

3. Lỗi Pinecone:
   - Kiểm tra API key và environment
   - Có thể comment tạm thời phần gọi Pinecone và thay bằng dữ liệu giả lập 