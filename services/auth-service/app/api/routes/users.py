from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.models.user import User
from app.schemas.base import BaseResponseModel
from app.schemas.user import UserUpdate, UserResponse
from app.services.user_service import UserService
from app.api.dependencies import get_current_user, get_current_admin_user
from app.db.database import get_db

router = APIRouter()


@router.get("/me", response_model=BaseResponseModel[UserResponse])
async def read_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user information."""
    
    if not current_user:
        return BaseResponseModel( 
            code=status.HTTP_403_FORBIDDEN,
            message="Unauthorized",
            errors="User not authenticated"
        )
        
    return BaseResponseModel[UserResponse](code=200, message="Success", data=current_user)


@router.put("/me", response_model=BaseResponseModel[UserResponse])
async def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user information."""
    # Check if email is being updated and already exists
    if user_in.email and user_in.email != current_user.email:
        if await UserService.get_user_by_email(db, user_in.email):
            return BaseResponseModel(
                code=400,
                message="Bad Request",
                errors="Email already registered"
            )

    # Check if username is being updated and already exists
    if user_in.username and user_in.username != current_user.username:
        if await UserService.get_user_by_username(db, user_in.username):
            return BaseResponseModel(
                code=400,
                message="Bad Request",
                errors="Username already taken"
            )

    user = await UserService.update_user(db, current_user.id, user_in)
    return BaseResponseModel[UserResponse](
        code=200,
        message="Success",
        data=user
    )


@router.get("", response_model=BaseResponseModel[List[UserResponse]])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get list of users."""
    users = await UserService.get_users(db, skip, limit)
    return BaseResponseModel[List[UserResponse]](
        code=status.HTTP_200_OK,
        message="Success",
        data=users
    )


@router.get("/{user_id}", response_model=BaseResponseModel[UserResponse])
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user by ID. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Not Found",
            errors="User not found"
        )
    return BaseResponseModel[UserResponse](
        code=status.HTTP_200_OK,
        message="Success",
        data=user
    )


@router.put("/{user_id}", response_model=BaseResponseModel[UserResponse])
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user information. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Not Found",
            errors="User not found"
        )

    # Check if email is being updated and already exists
    if user_in.email and user_in.email != user.email:
        if await UserService.get_user_by_email(db, user_in.email):
            return BaseResponseModel(
                code=400,
                message="Bad Request",
                errors="Email already registered"
            )

    # Check if username is being updated and already exists
    if user_in.username and user_in.username != user.username:
        if await UserService.get_user_by_username(db, user_in.username):
            return BaseResponseModel(
                code=400,
                message="Bad Request",
                errors="Username already taken"
            )

    user = await UserService.update_user(db, user_id, user_in)
    return BaseResponseModel[UserResponse](
        code=status.HTTP_200_OK,
        message="Success",
        data=user
    )


@router.delete("/{user_id}", response_model=BaseResponseModel[UserResponse])
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete user. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Not Found",
            errors="User not found"
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        return BaseResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Bad Request",
            errors="Cannot delete own account"
        )

    user = await UserService.delete_user(db, user_id)
    return BaseResponseModel[UserResponse](
        code=status.HTTP_200_OK,
        message="Success",
        data=user
    )


@router.post("/{user_id}/disable", response_model=BaseResponseModel[UserResponse])
async def disable_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Disable user account. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Not Found",
            errors="User not found"
        )

    # Prevent self-disabling
    if user.id == current_user.id:
        return BaseResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Bad Request",
            errors="Cannot disable own account"
        )

    user = await UserService.update_user(db, user_id, UserUpdate(disabled=True))
    return BaseResponseModel[UserResponse](
        code=status.HTTP_200_OK,
        message="Success",
        data=user
    )


@router.post("/{user_id}/enable", response_model=BaseResponseModel[UserResponse])
async def enable_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Enable user account. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        return BaseResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Not Found",
            errors="User not found"
        )

    user = await UserService.update_user(db, user_id, UserUpdate(disabled=False))
    return BaseResponseModel[UserResponse](
        code=status.HTTP_200_OK,
        message="Success",
        data=user
    )
