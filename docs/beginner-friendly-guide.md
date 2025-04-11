# Hướng Dẫn Chi Tiết Phát Triển Dự Án Cho Người Mới

## 1. Cài Đặt Môi Trường Ban Đầu

### 1.1 Cài đặt các công cụ cần thiết

1. **Python**
   - Truy cập [Python.org](https://www.python.org/downloads/)
   - Tải phiên bản Python mới nhất (ví dụ Python 3.9)
   - Chạy file cài đặt, nhớ tích vào ô "Add Python to PATH"
   - Kiểm tra cài đặt bằng cách mở Command Prompt và gõ:
   ```bash
   python --version
   ```

2. **Visual Studio Code**
   - Tải từ [code.visualstudio.com](https://code.visualstudio.com/)
   - Cài đặt các extensions:
     * Python
     * Python Extension Pack
     * Docker
     * Git

3. **PostgreSQL**
   - Tải từ [postgresql.org](https://www.postgresql.org/download/)
   - Trong quá trình cài đặt:
     * Ghi nhớ password cho user postgres
     * Chọn port mặc định 5432
     * Cài đặt pgAdmin 4 (công cụ quản lý đồ họa)

### 1.2 Khởi tạo Project

1. **Tạo thư mục project**
```bash
# Tạo và di chuyển vào thư mục project
mkdir my-project
cd my-project

# Tạo môi trường ảo Python
python -m venv venv

# Kích hoạt môi trường ảo
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

2. **Cài đặt các thư viện cần thiết**
```bash
# Cài đặt các package cơ bản
pip install fastapi[all] sqlalchemy psycopg2-binary python-dotenv pytest

# Lưu danh sách package đã cài
pip freeze > requirements.txt
```

## 2. Cấu Trúc Project

### 2.1 Tạo cấu trúc thư mục
```
my-project/
├── app/
│   ├── api/
│   │   ├── routes/      # Chứa các API endpoints
│   │   ├── models/      # Định nghĩa cấu trúc dữ liệu
│   │   └── schemas/     # Schemas cho request/response
│   ├── core/            # Cấu hình cốt lõi
│   ├── db/             # Database setup
│   └── services/       # Business logic
├── tests/             # Unit tests
├── .env              # Biến môi trường
└── requirements.txt  # Dependencies
```

**Tạo cấu trúc này bằng lệnh:**
```bash
# Windows
mkdir app app\api app\api\routes app\api\models app\api\schemas app\core app\db app\services tests

# macOS/Linux
mkdir -p app/api/routes app/api/models app/api/schemas app/core app/db app/services tests
```

### 2.2 Thiết lập file môi trường
Tạo file `.env`:
```env
# Database
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/my_database

# Application
APP_NAME=My Project
DEBUG=True
```

## 3. Kết Nối Database

### 3.1 Tạo Database

1. **Sử dụng pgAdmin 4:**
   - Mở pgAdmin 4
   - Chuột phải vào "Servers" > "PostgreSQL" > "Databases"
   - Chọn "Create" > "Database"
   - Đặt tên database là "my_database"

2. **Hoặc sử dụng command line:**
```bash
# Kết nối vào PostgreSQL
psql -U postgres

# Tạo database
CREATE DATABASE my_database;

# Kiểm tra database đã tạo
\l

# Thoát
\q
```

### 3.2 Setup Database trong Code

1. **Tạo file kết nối (app/db/database.py)**
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Tạo engine kết nối database
engine = create_engine(settings.DATABASE_URL)

# Tạo session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class cho các models
Base = declarative_base()

# Hàm tạo database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

2. **Tạo file cấu hình (app/core/config.py)**
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str
    DEBUG: bool
    DATABASE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## 4. Tạo Model và CRUD Cơ Bản

### 4.1 Tạo Model

File `app/api/models/user.py`:
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 4.2 Tạo Schema

File `app/api/schemas/user.py`:
```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True
```

### 4.3 Tạo CRUD Operations

File `app/services/user_service.py`:
```python
from sqlalchemy.orm import Session
from app.api.models.user import User
from app.api.schemas.user import UserCreate

class UserService:
    @staticmethod
    async def create_user(db: Session, user: UserCreate):
        db_user = User(
            email=user.email,
            full_name=user.full_name
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    async def get_user(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    async def get_users(db: Session, skip: int = 0, limit: int = 100):
        return db.query(User).offset(skip).limit(limit).all()
```

### 4.4 Tạo API Routes

File `app/api/routes/user.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.db.database import get_db

router = APIRouter()

@router.post("/users/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    return await UserService.create_user(db, user)

@router.get("/users/", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    users = await UserService.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = await UserService.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## 5. Chạy và Test API

### 5.1 Tạo Main Application

File `app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import user
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routes
app.include_router(user.router, prefix="/api/v1")
```

### 5.2 Chạy Application

1. **Khởi động server**
```bash
# Trong thư mục gốc của project
uvicorn app.main:app --reload
```

2. **Truy cập API Documentation**
- Mở trình duyệt và truy cập: http://localhost:8000/docs

### 5.3 Test API bằng curl

1. **Tạo user mới**
```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
     -H "Content-Type: application/json" \
     -d '{
           "email": "test@example.com",
           "full_name": "Test User",
           "password": "password123"
         }'
```

2. **Lấy danh sách users**
```bash
curl "http://localhost:8000/api/v1/users/"
```

## 6. Debugging và Troubleshooting

### 6.1 Lỗi Database

1. **Kiểm tra kết nối database**
```python
# Trong Python shell
from app.db.database import engine
try:
    connection = engine.connect()
    print("Kết nối thành công!")
    connection.close()
except Exception as e:
    print(f"Lỗi kết nối: {e}")
```

2. **Xem logs**
```python
# Thêm vào file database.py
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### 6.2 Common Errors

1. **Import Error**
   - Kiểm tra PYTHONPATH
   - Kiểm tra cấu trúc thư mục
   - Kiểm tra tên file và module

2. **Database Error**
   - Kiểm tra DATABASE_URL
   - Kiểm tra PostgreSQL service đang chạy
   - Kiểm tra firewall

3. **API Error**
   - Kiểm tra định dạng request
   - Xem logs trong terminal
   - Sử dụng Swagger UI để test

## 7. Best Practices

1. **Code Organization**
   - Mỗi function một nhiệm vụ
   - Tách biệt business logic và database operations
   - Sử dụng type hints

2. **Error Handling**
   - Luôn có try-except cho database operations
   - Return proper HTTP status codes
   - Log errors đầy đủ

3. **Security**
   - Không commit file .env
   - Sử dụng environment variables
   - Implement authentication/authorization

4. **Testing**
   - Viết unit tests
   - Test all API endpoints
   - Sử dụng test database riêng

## 8. Tài Liệu Tham Khảo

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Python Documentation](https://docs.python.org/)