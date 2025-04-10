# Auth Service 🔐

## Giới thiệu

Auth Service là microservice chịu trách nhiệm xác thực và phân quyền trong hệ thống AI JobMate. Service này cung cấp:
- Đăng ký và đăng nhập người dùng
- JWT authentication
- OAuth2 integration
- User management
- Role-based access control (RBAC)

## Tech Stack

- FastAPI
- PostgreSQL
- JWT
- OAuth2
- SQLAlchemy
- Alembic (migrations)

## Cấu trúc Project

```
auth-service/
├── alembic/           # Database migrations
├── src/
│   ├── api/          # API endpoints
│   ├── core/         # Core configurations
│   ├── crud/         # Database operations
│   ├── db/           # Database setup
│   ├── models/       # SQLAlchemy models
│   └── schemas/      # Pydantic schemas
├── tests/            # Unit & integration tests
├── Dockerfile
└── requirements.txt
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### Roles Table
```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB NOT NULL DEFAULT '{}'
);
```

## API Endpoints

### Authentication
- `POST /auth/register`: Đăng ký người dùng mới
- `POST /auth/login`: Đăng nhập
- `POST /auth/refresh-token`: Làm mới access token
- `POST /auth/logout`: Đăng xuất

### User Management
- `GET /users/me`: Lấy thông tin người dùng hiện tại
- `PUT /users/me`: Cập nhật thông tin người dùng
- `PUT /users/me/password`: Đổi mật khẩu

## Environment Variables

```env
# Database
POSTGRES_SERVER=postgres-auth
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=auth_service

# JWT
JWT_SECRET_KEY=your_jwt_secret
JWT_REFRESH_SECRET_KEY=your_refresh_secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

# Dependencies

```
fastapi
uvicorn
python-jose[cryptography]
passlib[bcrypt]
python-multipart
pydantic[email]
python-dotenv
pydantic-settings
sqlalchemy
psycopg2-binary
alembic
```

## Security Features

1. **Password Hashing**
   - Sử dụng Bcrypt với salt tự động
   - Minimum password length: 8 ký tự
   - Yêu cầu chữ hoa, chữ thường, số

2. **JWT Authentication**
   - Access token (30 phút)
   - Refresh token (7 ngày)
   - JWT signature verification
   - Token blacklisting for logout

3. **Rate Limiting**
   - 5 lần login attempt/phút
   - 3 lần reset password/giờ

4. **Database Security**
   - Prepared statements
   - SQL injection prevention
   - Connection pooling
   - SSL/TLS encryption

## Development

1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

2. Chạy migrations:
```bash
alembic upgrade head
```

3. Start development server:
```bash
uvicorn main:app --reload --port 8001
```

## Testing

```bash
# Unit tests
pytest

# Security tests
pytest tests/security/

# Integration tests
pytest tests/integration/
```

## Monitoring

- Endpoint metrics: http://localhost:8001/metrics
- Health check: http://localhost:8001/health

## Logging

Các events được log:
- Authentication attempts
- Password changes
- Role changes
- Token generation/refresh
- Security violations

## Error Handling

Common error codes:
- `401`: Unauthorized
- `403`: Forbidden
- `422`: Validation Error
- `429`: Too Many Requests

## Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes với conventional commits
4. Update tests
5. Tạo Pull Request

### Security Guidelines
- Không commit secrets
- Luôn sử dụng prepared statements
- Validate tất cả input
- Log security events
- Regular dependency updates