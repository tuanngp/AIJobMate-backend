from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_token
from app.db.session import SessionLocal
from app.models.user import User

# Cấu hình OAuth2PasswordBearer với endpoint login
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

# Dependency để lấy DB session
def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

# Dependency để lấy thông tin current user từ access token
def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        # Xác thực access token
        payload = verify_token(token, token_type="access")
        user = db.query(User).filter(User.id == payload.get("sub")).first()
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Người dùng không hoạt động")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác thực thông tin đăng nhập",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependency để lấy thông tin current user từ refresh token
def get_current_user_from_refresh_token(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        # Xác thực refresh token
        payload = verify_token(token, token_type="refresh")
        user = db.query(User).filter(User.id == payload.get("sub")).first()
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Người dùng không hoạt động")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không thể xác thực refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Dependency để kiểm tra nếu user là superuser
def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="Người dùng không có quyền quản trị"
        )
    return current_user 