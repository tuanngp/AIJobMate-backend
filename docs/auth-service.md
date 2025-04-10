# Auth Service Documentation

## 1. Tổng quan / Overview

### Mục đích / Purpose
Auth Service là microservice chịu trách nhiệm quản lý xác thực và phân quyền người dùng trong hệ thống AI JobMate. Service này cung cấp các chức năng đăng ký, đăng nhập, và quản lý token JWT.

### Công nghệ sử dụng / Technologies
- Framework: FastAPI
- Database: PostgreSQL
- Authentication: JWT (JSON Web Tokens)
- ORM: SQLAlchemy
- Migration: Alembic

## 2. Quy trình xử lý / Processing Flow

### Đăng ký / Registration Flow
1. Client gửi thông tin đăng ký
2. Validate dữ liệu đầu vào
3. Kiểm tra email đã tồn tại
4. Hash mật khẩu
5. Lưu thông tin user vào database
6. Trả về thông báo thành công

### Đăng nhập / Login Flow
1. Client gửi credentials
2. Validate thông tin đăng nhập
3. Kiểm tra password hash
4. Tạo access token và refresh token
5. Lưu refresh token vào database
6. Trả về tokens

### Làm mới token / Refresh Token Flow
1. Client gửi refresh token
2. Validate refresh token
3. Kiểm tra token trong database
4. Tạo access token mới
5. Trả về access token mới

## 3. API Endpoints

### POST /auth/register
Đăng ký tài khoản mới

**Request Schema:**
```json
{
  "email": "string",
  "password": "string",
  "full_name": "string",
  "phone": "string?"
}
```

**Response Schema:**
```json
{
  "id": "uuid",
  "email": "string",
  "full_name": "string",
  "created_at": "datetime"
}
```

### POST /auth/login
Đăng nhập và nhận tokens

**Request Schema:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response Schema:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer"
}
```

### POST /auth/refresh-token
Làm mới access token

**Request Schema:**
```json
{
  "refresh_token": "string"
}
```

**Response Schema:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

## 4. Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### RefreshTokens Table
```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    token VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, token)
);
```

## 5. Service Dependencies

### Required Services
- PostgreSQL Database (auth_service database)

### External Dependencies
Không có

## 6. API Integration Requirements

### Headers
```
Content-Type: application/json
Authorization: Bearer <access_token> (cho protected endpoints)
```

### Validation Rules
- Email: Hợp lệ và unique
- Password: Tối thiểu 8 ký tự, có chữ hoa, chữ thường và số
- Phone: Định dạng số điện thoại Việt Nam (tùy chọn)

### Status Codes
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Validation Error
- 500: Internal Server Error

### Error Response Format
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {} 
  }
}
```

### Rate Limiting
- 100 requests/minute cho đăng ký và đăng nhập
- 300 requests/minute cho refresh token

## 7. Service Communication

### Communication Type
- REST APIs (Synchronous)
- HTTP/HTTPS

### Retry Policy
- Maximum 3 retries
- Exponential backoff: 1s, 2s, 4s
- Jitter: 0-500ms

### Timeout Configuration
- Database queries: 5 seconds
- API endpoints: 10 seconds
- Token verification: 2 seconds

### Circuit Breaker
- Threshold: 50% failure rate
- Reset timeout: 30 seconds
- Half-open state: Allow 3 requests

## 8. Monitoring & Logging

### Health Check Endpoint
GET /health
```json
{
  "status": "healthy",
  "version": "string",
  "database": "connected",
  "timestamp": "datetime"
}
```

### Metrics
- Request count và latency
- Database connection pool status
- Token creation/verification time
- Error rates và types

### Logging
- Request logs (excluding sensitive data)
- Authentication attempts
- Token operations
- Database errors
- Service errors