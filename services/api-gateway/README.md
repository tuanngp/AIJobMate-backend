# API Gateway Service 🔗

## Giới thiệu

API Gateway là điểm vào chính của hệ thống AI JobMate, đảm nhiệm việc:
- Điều hướng requests tới các microservices
- Xác thực và phân quyền
- Rate limiting và caching
- API documentation

## Cấu trúc Project

```
api-gateway/
├── src/
│   ├── auth/         # Authentication middleware
│   ├── routes/       # API routes
│   ├── services/     # Service integrations
│   └── utils/        # Utility functions
├── tests/            # Unit & integration tests
├── Dockerfile        # Container configuration
└── requirements.txt  # Dependencies
```

## Dependencies

```
fastapi
uvicorn
httpx
python-multipart
python-dotenv
prometheus-client
```

## API Endpoints

### Authentication
- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh-token`

### Career Advisor
- `POST /career/analyze`
- `GET /career/recommendations`
- `POST /career/feedback`

### Health Check
- `GET /health`

## Environment Variables

```env
AUTH_SERVICE_URL=http://auth-service:8001
CAREER_ADVISOR_SERVICE_URL=http://career-advisor-service:8002
FRONTEND_URL=http://localhost:3000
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## Development

1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

2. Chạy development server:
```bash
uvicorn main:app --reload --port 8000
```

## Testing

```bash
# Unit tests
pytest

# Coverage report
pytest --cov=src
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Performance Monitoring

- Endpoint metrics: http://localhost:8000/metrics
- Health check: http://localhost:8000/health

## Rate Limiting

Default settings:
- 100 requests/minute cho authenticated users
- 20 requests/minute cho anonymous users

## Logging

Logs được ghi theo format:
```
[TIMESTAMP] [LEVEL] [REQUEST_ID] message
```

## Security

- JWT authentication
- CORS protection
- Rate limiting
- Request validation
- SQL injection prevention

## Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes với conventional commits
4. Push to branch
5. Tạo Pull Request