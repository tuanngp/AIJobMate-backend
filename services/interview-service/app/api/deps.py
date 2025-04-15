import json
import logging
from typing import Generator, Optional

import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User

# Cấu hình logging
logger = logging.getLogger(__name__)

# OAuth2 scheme
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.AUTH_SERVICE_URL}/auth/login"
)

def get_db() -> Generator:
    """
    Dependency để lấy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """
    Dependency để lấy thông tin người dùng hiện tại từ token
    """
    try:
        # Gọi đến auth service để validate token
        auth_url = f"{settings.AUTH_SERVICE_URL}/auth/verify"
        logger.info(f"Calling auth service at: {auth_url}")
        
        response = requests.get(
            auth_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        
        if response.status_code != 200:
            logger.error(f"Auth service response: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token không hợp lệ",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user_data = response.json()
        logger.info(f"Auth service returned user data: {user_data}")
        
        # Kiểm tra user trong database local
        user = db.query(User).filter(User.id == user_data["id"]).first()
        
        # Nếu user chưa có trong database, tạo mới
        if not user:
            user = User(
                id=user_data["id"],
                username=user_data.get("username", "unknown"),
                email=user_data.get("email", "unknown@example.com"),
                full_name=user_data.get("full_name", ""),
                skills=json.dumps(user_data.get("skills", [])),
                experience=json.dumps(user_data.get("experience", [])),
                education=json.dumps(user_data.get("education", [])),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return user
        
    except Exception as e:
        logger.error(f"Lỗi khi xác thực người dùng: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác thực người dùng",
            headers={"WWW-Authenticate": "Bearer"},
        ) 