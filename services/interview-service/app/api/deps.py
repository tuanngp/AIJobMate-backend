import json
from typing import Dict, Any
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

# Dependency để lấy DB session
def get_db() -> Session:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

async def get_current_user(
    request: Request
) -> Dict[str, Any]:
    """
    Lấy thông tin user từ request header được set bởi API Gateway
    sau khi verify token với auth service.
    """
    user_info = request.headers.get("X-User-Info")
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không có thông tin xác thực"
        )
    
    try:
        # Parse và xử lý user info
        user_info = json.loads(user_info)
        
        # Map thông tin user về đúng format
        processed_info = {
            "id": user_info.get("id"),  # id từ verify endpoint
            "permissions": user_info.get("roles", []),  # roles -> permissions
            "exp": user_info.get("exp"),
            "type": user_info.get("type")
        }
        
        return processed_info
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user info format"
        )

def check_permissions(required_permissions: list[str]):
    """
    Kiểm tra permissions từ user info trong header.
    """
    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        user_permissions = current_user.get("permissions", [])
        for permission in required_permissions:
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Không có quyền: {permission}"
                )
        return current_user
    return permission_checker

async def get_current_superuser(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Kiểm tra nếu user có quyền admin từ user info.
    """
    if "admin" not in current_user.get("permissions", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yêu cầu quyền admin"
        )
    return current_user