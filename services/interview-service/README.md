# AI Interview Service

Service AI Interview Practice cung cấp tính năng tạo và phân tích câu hỏi phỏng vấn sử dụng AI.

## Tính năng chính

- **Tạo câu hỏi phỏng vấn tự động**: Tạo các câu hỏi phỏng vấn dựa trên vị trí công việc, mô tả công việc, và các yêu cầu kỹ năng.
- **Hỗ trợ nhiều loại phỏng vấn**: Technical, behavioral, và mixed.
- **Phân tích câu trả lời**: Đánh giá câu trả lời của người dùng và đưa ra phản hồi.
- **Quản lý phỏng vấn**: Lưu trữ và quản lý các buổi phỏng vấn.

## API Endpoints

### Tạo câu hỏi phỏng vấn

```
POST /api/v1/interviews/generate
```

Request body:
```json
{
  "job_title": "Software Engineer",
  "job_description": "We are looking for a software engineer...",
  "industry": "Technology",
  "num_questions": 5,
  "difficulty_level": "medium",
  "interview_type": "technical",
  "skills_required": ["Python", "SQL", "Docker"]
}
```

### Lấy danh sách phỏng vấn

```
GET /api/v1/interviews
```

### Lấy chi tiết phỏng vấn

```
GET /api/v1/interviews/{interview_id}
```

### Phân tích câu trả lời

```
POST /api/v1/interviews/{interview_id}/questions/{question_id}/analyze
```

Request body:
```json
{
  "user_answer": "Câu trả lời của người dùng..."
}
```

### Xóa phỏng vấn

```
DELETE /api/v1/interviews/{interview_id}
```

## Cài đặt và chạy ứng dụng

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Cấu hình môi trường

Tạo file `.env` dựa trên `.env.example` và điền các thông tin cấu hình cần thiết.

### Chạy ứng dụng

```bash
python run.py
```

hoặc

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## Cấu trúc thư mục

```
interview-service/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── interviews.py
│   │   └── deps.py
│   ├── core/
│   │   └── config.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── interview.py
│   │   ├── interview_question.py
│   │   └── user.py
│   ├── schemas/
│   │   └── interview.py
│   ├── services/
│   │   ├── openai_service.py
│   │   └── redis_service.py
│   └── main.py
├── .env
├── requirements.txt
├── run.py
└── Dockerfile
``` 