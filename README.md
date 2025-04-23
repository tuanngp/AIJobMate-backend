# AI Job Mate Backend 🚀

[![FastAPI](https://img.shields.io/badge/FastAPI-0.68.0-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![NestJS](https://img.shields.io/badge/NestJS-8.0.0-E0234E.svg?style=flat&logo=nestjs)](https://nestjs.com)
[![Docker](https://img.shields.io/badge/Docker-20.10.8-2496ED.svg?style=flat&logo=docker)](https://www.docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D.svg?style=flat&logo=redis)](https://redis.io)

AI JobMate là nền tảng hỗ trợ sự nghiệp thông minh, tích hợp công nghệ AI tiên tiến để giúp người dùng phát triển sự nghiệp hiệu quả.

## 📑 Mục lục

- [Tổng quan](#-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Hướng dẫn cài đặt](#-hướng-dẫn-cài-đặt)
- [Cấu hình môi trường](#-cấu-hình-môi-trường)
- [API Documentation](#-api-documentation)
- [Quản lý Docker](#-quản-lý-docker)
- [Monitoring & Logs](#-monitoring--logs)
- [Xử lý sự cố](#-xử-lý-sự-cố)
- [Contributing Guidelines](#-contributing-guidelines)

## 🌟 Tổng quan

AI JobMate cung cấp các tính năng chính:

- 🎯 Tư vấn nghề nghiệp với AI
- 🎤 Thực hành phỏng vấn với AI
- 📹 Huấn luyện phỏng vấn video
- 💼 Gợi ý việc làm và dự đoán lương
- 🔐 Xác thực và bảo mật

## 🏗 Kiến trúc hệ thống

### Microservices

1. **AI Career Advisor Service** (Port: 8002)
   - Framework: FastAPI
   - Database: PostgreSQL
   - Cache: Redis
   - External APIs: OpenRouter (GPT), Pinecone
   - Chức năng: Phân tích và tư vấn nghề nghiệp

2. **Authentication Service** (Port: 8001)
   - Framework: FastAPI
   - Database: PostgreSQL
   - JWT & OAuth2
   - Chức năng: Quản lý người dùng và xác thực

3. **Interview Service** (Port: 8003)
   - Framework: FastAPI
   - Cache: Redis
   - External APIs: OpenRouter (GPT)
   - Chức năng: Thực hành phỏng vấn với AI

4. **API Gateway** (Port: 8000)
   - Reverse proxy và load balancing
   - Rate limiting và caching
   - Request routing
   - API documentation (Swagger)

### Databases & Caching

- **PostgreSQL**
  - auth_service: Dữ liệu người dùng
  - career_advisor_service: Dữ liệu nghề nghiệp
  
- **Redis**
  - Caching
  - Queue management
  - Rate limiting

## 💻 Yêu cầu hệ thống

- Docker Engine (≥ 20.10.8)
- Docker Compose (≥ 2.0.0)
- Tài khoản các dịch vụ:
  - OpenRouter (GPT API)
  - Pinecone (Vector Database)
- RAM: Tối thiểu 4GB
- CPU: 2 cores trở lên
- Dung lượng ổ cứng: 10GB trở lên

## 🚀 Hướng dẫn cài đặt

1. Clone repository:
```bash
git clone https://github.com/your-org/ai-jobmate.git
cd ai-jobmate/backend
```

2. Tạo file môi trường:
```bash
cp .env.example .env
```

3. Build và khởi động services:
```bash
docker-compose up -d --build
```

4. Kiểm tra trạng thái:
```bash
docker-compose ps
```

## ⚙️ Cấu hình môi trường

File `.env` cần có các biến môi trường chính sau:

```env
# Database configurations
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# Database names
POSTGRES_AUTH_DB=auth_service
POSTGRES_CAREER_ADVISOR_DB=career_advisor_service

# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_INTERVIEW_DB=1

# AI Services
OPENROUTER_API_KEY=your_openrouter_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=your_pinecone_env
PINECONE_INDEX=career-advisor

# Security settings
JWT_SECRET_KEY=your_jwt_secret_min_32_chars
JWT_REFRESH_SECRET_KEY=your_refresh_secret_min_32_chars
```

## 🐳 Quản lý Docker

### Development Workflow

1. **Hot Reload Development:**
```bash
# Khởi động với volume mounts cho hot reload
docker-compose up -d
```

2. **Rebuild Service Cụ thể:**
```bash
# Rebuild và restart một service
docker-compose up -d --build [service-name]
```

3. **Clean Environment:**
```bash
# Xóa tất cả containers, images và volumes
docker-compose down -v --rmi all
```

### Resource Management

Mỗi service được cấu hình với resource limits để tránh quá tải:

- API Gateway: 0.5 CPU, 512MB RAM
- Auth Service: 0.5 CPU, 512MB RAM
- Career Advisor: 0.75 CPU, 1GB RAM
- Interview Service: 0.75 CPU, 1GB RAM
- PostgreSQL: 0.5 CPU, 512MB RAM
- Redis: 0.25 CPU, 256MB RAM

### Xem logs

```bash
# Xem logs của một service cụ thể
docker-compose logs -f [service-name]

# Xem logs của toàn bộ hệ thống
docker-compose logs -f
```

### Quản lý containers

```bash
# Dừng hệ thống
docker-compose down

# Khởi động lại một service
docker-compose restart [service-name]

# Xóa volumes và khởi động lại
docker-compose down -v
docker-compose up -d
```

## 📊 Monitoring & Logs

### Health Checks

Mỗi service đều có endpoint kiểm tra sức khỏe:
- API Gateway: http://localhost:8000/health
- Auth Service: http://localhost:8001/health
- Career Advisor: http://localhost:8002/health
- Interview Service: http://localhost:8003/health

### Metrics

- PostgreSQL metrics: localhost:8001/metrics
- Redis metrics: localhost:6379/metrics
- Application metrics: localhost:8000/metrics

## 🔧 Xử lý sự cố

### 1. Service không khởi động

```bash
# Kiểm tra logs
docker-compose logs -f [service-name]

# Kiểm tra environment variables
docker-compose config
```

### 2. Database Connection Issues

```bash
# Kiểm tra PostgreSQL
docker-compose exec postgres-auth psql -U [user] -d auth_service

# Kiểm tra Redis
docker-compose exec redis redis-cli ping
```

### 3. API Gateway Issues

- Kiểm tra các service dependencies
- Xác nhận các URL trong môi trường
- Kiểm tra CORS settings

## 🤝 Contributing Guidelines

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

### Coding Standards

- Sử dụng Black cho Python code formatting
- Tuân thủ PEP 8
- 100% test coverage cho code mới
- Semantic versioning

### Testing

```bash
# Unit tests
docker-compose exec [service-name] pytest

# Integration tests
docker-compose -f docker-compose.test.yml up --build
```

## 📝 License

[MIT License](LICENSE)

---
Made with ❤️ by AI JobMate Team