from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Tạo SQLAlchemy engine
engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)

# Tạo session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Định nghĩa Base class cho các models
Base = declarative_base() 