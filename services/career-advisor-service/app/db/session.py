from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Tạo engine cho SQLAlchemy
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,  # Kiểm tra kết nối trước khi sử dụng
    pool_size=5,         # Kích thước pool kết nối
    max_overflow=10,     # Số kết nối tối đa có thể vượt quá pool_size
    pool_recycle=3600,   # Recycle kết nối sau 1 giờ để tránh lỗi kết nối hết thời gian
)

# Tạo session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency để cung cấp database session cho mỗi request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()