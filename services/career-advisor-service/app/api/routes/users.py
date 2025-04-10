from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user, check_permissions
from app.clients.auth_client import auth_client

router = APIRouter()

@router.get("/me")
async def read_user_me(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Lấy thông tin người dùng hiện tại từ request header.
    """
    return current_user

@router.put("/me")
async def update_user_me(
    *,
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Redirect người dùng tới auth service để cập nhật thông tin.
    """
    from app.core.config import settings
    raise HTTPException(
        status_code=307,  # Temporary Redirect
        detail=f"{settings.AUTH_SERVICE_URL}/api/v1/users/me"
    )

@router.get("/{user_id}")
async def read_user_by_id(
    user_id: str,
    _: dict = Depends(check_permissions(["manage_users"]))
) -> Any:
    """
    Lấy thông tin người dùng theo ID (yêu cầu quyền manage_users).
    """
    try:
        user_info = await auth_client.get_user_info_by_id(user_id)
        return user_info
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy thông tin user từ auth service: {str(e)}"
        )

@router.get("/", response_model=List[dict])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    _: dict = Depends(check_permissions(["manage_users"]))
) -> Any:
    """
    Lấy danh sách người dùng (yêu cầu quyền manage_users).
    """
    try:
        users = await auth_client.list_users(skip=skip, limit=limit)
        return users
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy danh sách users từ auth service: {str(e)}"
        )