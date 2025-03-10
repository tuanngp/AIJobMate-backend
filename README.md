# AI JobMate - Backend Infrastructure

Đây là backend infrastructure cho AI JobMate, một nền tảng hỗ trợ sự nghiệp sử dụng công nghệ AI.

## Kiến trúc Microservices

Hệ thống bao gồm các microservices sau:

1. **AI Career Advisor Service**
   - Framework: FastAPI
   - Chức năng: Tư vấn nghề nghiệp thông qua AI
   - Công nghệ: OpenAI GPT-4, Vector Database (Pinecone/Milvus)

2. **AI Interview Practice Service**
   - Framework: NestJS
   - Chức năng: Thực hành phỏng vấn với AI
   - Công nghệ: OpenAI Whisper API, WebSockets, TensorFlow.js

3. **AI Video Interview Coach Service**
   - Framework: FastAPI với Starlette
   - Chức năng: Huấn luyện phỏng vấn video
   - Công nghệ: CLIP model, FFmpeg, ONNX Runtime

4. **Job Matching & Salary Prediction Service**
   - Framework: FastAPI
   - Chức năng: Gợi ý việc làm và dự đoán lương
   - Công nghệ: XGBoost, MLflow, Redis, Apache Airflow

5. **API Gateway & Authentication Service**
   - Chức năng: Quản lý API và xác thực người dùng
   - Công nghệ: AWS API Gateway, OAuth 2.0 + JWT

6. **Data Storage & Caching Service**
   - Chức năng: Lưu trữ và cache dữ liệu
   - Công nghệ: PostgreSQL, Redis, SQLAlchemy, Alembic

## Cài đặt và Phát triển

### Yêu cầu hệ thống
- Python 3.9+
- Node.js 16+
- Docker và Docker Compose
- AWS CLI (cho triển khai)

### Cài đặt môi trường phát triển
```bash
# Clone repository
git clone https://github.com/your-organization/ai-jobmate.git
cd ai-jobmate/backend

# Cài đặt dependencies cho từng service
# Xem README.md trong từng thư mục service
```

### Chạy hệ thống với Docker Compose
```bash
docker-compose up
```

## API Documentation
Sau khi chạy hệ thống, bạn có thể truy cập tài liệu API tại:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Triển khai
Hệ thống được thiết kế để triển khai trên AWS với các dịch vụ như:
- AWS Lambda
- AWS ECS/Fargate
- AWS SageMaker
- AWS API Gateway
- AWS RDS (PostgreSQL)
- AWS ElastiCache (Redis)

## Giám sát và Observability
- Distributed tracing với AWS X-Ray
- Monitoring với Prometheus
- Logging tập trung với AWS CloudWatch

## CI/CD
Dự án sử dụng GitHub Actions cho CI/CD với automated testing và deployment. 