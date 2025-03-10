import json
from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_current_active_superuser
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import User as UserSchema, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserSchema)
def read_user_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Lấy thông tin người dùng hiện tại.
    """
    return current_user


@router.put("/me", response_model=UserSchema)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    user_in: UserUpdate,
) -> Any:
    """
    Cập nhật thông tin người dùng hiện tại.
    """
    # Tạo từ điển với các giá trị cần cập nhật
    update_data = user_in.dict(exclude_unset=True)
    
    # Nếu có password mới, hash password
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        update_data["hashed_password"] = hashed_password
        del update_data["password"]
    
    # Chuyển đổi các trường dạng danh sách/từ điển thành JSON
    for field in ["skills", "experiences", "education", "career_goals", "preferred_industries"]:
        if field in update_data and update_data[field] is not None:
            update_data[field] = json.dumps(update_data[field])
    
    # Cập nhật user
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserSchema)
def read_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Lấy thông tin người dùng theo ID (chỉ dành cho admin).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy người dùng",
        )
    return user


@router.get("/", response_model=List[UserSchema])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Lấy danh sách người dùng (chỉ dành cho admin).
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users 