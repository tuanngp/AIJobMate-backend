# AI JobMate - Đề xuất Services mới / Proposed New Services

## 1. Interview Practice Service

### Mục đích / Purpose
Cung cấp môi trường thực hành phỏng vấn với AI, cho phép người dùng luyện tập và nhận feedback chi tiết.

### Justification
- Tăng tỷ lệ thành công trong phỏng vấn cho người dùng
- Cung cấp môi trường thực hành không giới hạn
- Thu thập data về xu hướng câu hỏi phỏng vấn

### Proposed API Endpoints

```yaml
POST /interviews/sessions:
  - Tạo phiên phỏng vấn mới
  - Chọn vị trí và level
  - Thiết lập các tham số phỏng vấn

POST /interviews/questions:
  - Nhận câu hỏi tiếp theo
  - Phân tích câu trả lời
  - Cung cấp feedback

GET /interviews/history:
  - Xem lịch sử phỏng vấn
  - Thống kê performance
  - Tracking tiến độ

POST /interviews/feedback:
  - Đánh giá chất lượng phỏng vấn
  - Góp ý cải thiện
```

### Database Schema
```sql
CREATE TABLE interview_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    position VARCHAR(255),
    level VARCHAR(50),
    status VARCHAR(50),
    score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE interview_questions (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES interview_sessions(id),
    question TEXT,
    answer TEXT,
    feedback TEXT,
    score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE
);
```

### Dependencies
- OpenRouter API (GPT)
- Auth Service
- Career Advisor Service (optional)
- Speech-to-Text Service (future)

## 2. Video Interview Service

### Mục đích / Purpose
Cho phép người dùng thực hành phỏng vấn qua video, với phân tích biểu cảm khuôn mặt, giọng nói và ngôn ngữ cơ thể.

### Justification
- Tạo môi trường phỏng vấn thực tế
- Phân tích các yếu tố phi ngôn ngữ
- Cải thiện kỹ năng giao tiếp

### Proposed API Endpoints

```yaml
POST /video-interviews/start:
  - Khởi tạo phiên video
  - Thiết lập thông số recording
  - Cấu hình AI analysis

POST /video-interviews/analyze:
  - Upload video segment
  - Phân tích realtime
  - Feedback tức thời

GET /video-interviews/reports:
  - Báo cáo chi tiết
  - Metrics và đánh giá
  - Đề xuất cải thiện
```

### Database Schema
```sql
CREATE TABLE video_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    video_url TEXT,
    duration INTEGER,
    analysis_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE video_analytics (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES video_sessions(id),
    timestamp INTEGER,
    expression VARCHAR(50),
    voice_metrics JSONB,
    body_language_metrics JSONB,
    confidence_score FLOAT
);
```

### Dependencies
- Video Processing Service
- Face Analysis API
- Voice Analysis API
- Cloud Storage Service

## 3. Job Market Analytics Service

### Mục đích / Purpose
Phân tích và dự báo xu hướng thị trường việc làm, mức lương, và kỹ năng cần thiết.

### Justification
- Cung cấp insight cho người tìm việc
- Hỗ trợ quyết định career path
- Data-driven career planning

### Proposed API Endpoints

```yaml
GET /market/trends:
  - Xu hướng ngành nghề
  - Biến động thị trường
  - Dự báo tương lai

GET /market/salary:
  - Thống kê mức lương
  - So sánh theo vị trí/khu vực
  - Dự báo tăng trưởng

GET /market/skills:
  - Hot skills analysis
  - Skill gaps
  - Learning recommendations
```

### Database Schema
```sql
CREATE TABLE market_trends (
    id UUID PRIMARY KEY,
    industry VARCHAR(255),
    trend_data JSONB,
    forecast_data JSONB,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE salary_data (
    id UUID PRIMARY KEY,
    position VARCHAR(255),
    location VARCHAR(255),
    salary_range JSONB,
    trend_coefficient FLOAT,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Dependencies
- External Job Market APIs
- Data Analysis Service
- Machine Learning Pipeline
- Career Advisor Service

## 4. Learning Path Service

### Mục đích / Purpose
Tạo và quản lý lộ trình học tập cá nhân hóa dựa trên mục tiêu nghề nghiệp.

### Justification
- Định hướng phát triển rõ ràng
- Tối ưu hóa quá trình học tập
- Tracking tiến độ học tập

### Priority & Timeline
- Priority: Medium
- Timeline: Q1 2025
- Estimated Development Time: 3 months

### Proposed API Endpoints

```yaml
POST /learning/paths:
  - Tạo lộ trình học tập
  - Customize theo mục tiêu
  - Tích hợp resources

GET /learning/progress:
  - Track tiến độ
  - Đánh giá kết quả
  - Điều chỉnh lộ trình

POST /learning/feedback:
  - Đánh giá hiệu quả
  - Góp ý cải thiện
  - Cập nhật preferences
```

### Database Schema
```sql
CREATE TABLE learning_paths (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    career_goal TEXT,
    path_data JSONB,
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE learning_progress (
    id UUID PRIMARY KEY,
    path_id UUID REFERENCES learning_paths(id),
    module_id VARCHAR(255),
    status VARCHAR(50),
    score FLOAT,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

### Dependencies
- Career Advisor Service
- External Learning Platforms
- Assessment Service
- Progress Tracking System

## Service Communication Patterns

### Synchronous Communication
- RESTful APIs với retry và circuit breaker
- GraphQL cho complex queries
- gRPC cho high-performance services

### Asynchronous Communication
- Message queues cho long-running tasks
- Event streaming cho real-time updates
- Webhooks cho external integrations

### Integration Requirements
- Unified API gateway
- Consistent error handling
- Centralized logging
- Distributed tracing
- Performance monitoring