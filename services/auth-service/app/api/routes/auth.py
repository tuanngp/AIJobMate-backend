from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user_from_refresh_token
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    blacklist_token,
)
from app.models.user import User
from app.schemas.token import Token, RefreshToken
from app.schemas.user import User as UserSchema, UserCreate

router = APIRouter()


@router.post("/register", response_model=UserSchema)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Đăng ký người dùng mới.
    """
    # Kiểm tra nếu email đã tồn tại
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email đã được sử dụng",
        )
        
    # Tạo người dùng mới
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        is_active=True,
        is_superuser=False,
        profile_metadata=user_in.profile_metadata
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, lấy access token và refresh token cho future requests.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không chính xác")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không chính xác")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Tài khoản không hoạt động")
        
    # Tạo access token và refresh token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_refresh_token),
    refresh_token_in: RefreshToken,
) -> Any:
    """
    Refresh access token bằng refresh token.
    """
    # Blacklist refresh token cũ
    blacklist_token(refresh_token_in.refresh_token)
    
    # Tạo access token và refresh token mới
    access_token = create_access_token(current_user.id)
    refresh_token = create_refresh_token(current_user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    *,
    current_user: User = Depends(get_current_user_from_refresh_token),
    refresh_token_in: RefreshToken,
) -> Any:
    """
    Đăng xuất bằng cách blacklist refresh token.
    """
    # Blacklist refresh token
    blacklist_token(refresh_token_in.refresh_token)
    
    return {"message": "Đăng xuất thành công"} 