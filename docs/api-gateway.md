# API Gateway Service Documentation

## 1. Tổng quan / Overview

### Mục đích / Purpose
API Gateway đóng vai trò là điểm vào chính của hệ thống AI JobMate, xử lý việc định tuyến request, load balancing, authentication, và rate limiting. Service này đảm bảo tính bảo mật và hiệu suất cho toàn bộ hệ thống.

### Công nghệ sử dụng / Technologies
- Framework: FastAPI
- Cache: Redis
- Load Balancer: Built-in FastAPI
- Documentation: Swagger/OpenAPI

## 2. Quy trình xử lý / Processing Flow

### Request Flow
1. Nhận request từ client
2. Kiểm tra rate limit
3. Xác thực JWT token (nếu cần)
4. Định tuyến request đến service phù hợp
5. Nhận response từ service
6. Cache response (nếu cần)
7. Trả về kết quả cho client

### Error Handling Flow
1. Bắt lỗi từ các services
2. Chuẩn hóa format lỗi
3. Log lỗi
4. Trả về error response

## 3. Route Configuration

### Authentication Routes
```yaml
/api/v1/auth/*:
  target: http://auth-service:8001
  auth_required: false
  rate_limit: 100/minute
```

### Career Advisor Routes
```yaml
/api/v1/career/*:
  target: http://career-advisor-service:8002
  auth_required: true
  rate_limit: 200/minute
```

## 4. Service Dependencies

### Required Services
- Auth Service
- AI Career Advisor Service
- Redis (cho rate limiting và caching)

### Communication
- Internal network: backend
- Protocol: HTTP/HTTPS
- Load balancing: Round-robin

## 5. API Integration Requirements

### Global Headers
```
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json
X-Request-ID: <uuid>
```

### Response Headers
```
X-Rate-Limit-Limit: <number>
X-Rate-Limit-Remaining: <number>
X-Rate-Limit-Reset: <timestamp>
```

### CORS Configuration
```json
{
  "allow_origins": ["http://localhost:3000"],
  "allow_methods": ["GET", "POST", "PUT", "DELETE"],
  "allow_headers": ["*"],
  "max_age": 600
}
```

### Rate Limiting
- Default: 1000 requests/minute/IP
- Auth endpoints: 100 requests/minute/IP
- Career endpoints: 200 requests/minute/IP

## 6. Monitoring & Security

### Health Checks
- Interval: 30 seconds
- Timeout: 10 seconds
- Unhealthy threshold: 3
- Path: /health

### Security Measures
- JWT Validation
- Rate Limiting
- IP Whitelisting (optional)
- Request size limits
- Timeout policies

### Logging
- Request logs
- Error logs
- Performance metrics
- Security events

## 7. Future Improvements

### Planned Features
- GraphQL support
- WebSocket Gateway
- Service Discovery
- Circuit Breaker implementation
- Enhanced monitoring

## 8. Service Communication

### Timeout Configuration
- Default: 30 seconds
- Auth service: 10 seconds
- Career service: 45 seconds

### Circuit Breaker
- Threshold: 50% failure rate
- Reset timeout: 30 seconds
- Half-open state: Allow 3 requests

### Retry Policy
- Maximum 3 retries
- Exponential backoff
- Jitter: 0-500ms