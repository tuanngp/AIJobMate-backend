from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Any
from app.core.security import verify_token
from app.models.user import User, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.api.dependencies import get_current_user, get_current_admin_user
from app.db.database import get_db

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current user information."""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update current user information."""
    # Check if email is being updated and already exists
    if user_in.email and user_in.email != current_user.email:
        if await UserService.get_user_by_email(db, user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Check if username is being updated and already exists
    if user_in.username and user_in.username != current_user.username:
        if await UserService.get_user_by_username(db, user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    user = await UserService.update_user(db, current_user.id, user_in)
    return user

@router.get("", response_model=List[UserResponse])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get list of users. Admin only."""
    users = await UserService.get_users(db, skip, limit)
    return users

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user by ID. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Update user information. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email is being updated and already exists
    if user_in.email and user_in.email != user.email:
        if await UserService.get_user_by_email(db, user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Check if username is being updated and already exists
    if user_in.username and user_in.username != user.username:
        if await UserService.get_user_by_username(db, user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    user = await UserService.update_user(db, user_id, user_in)
    return user

@router.delete("/{user_id}", response_model=UserResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Delete user. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete own account"
        )
    
    user = await UserService.delete_user(db, user_id)
    return user

@router.post("/{user_id}/disable", response_model=UserResponse)
async def disable_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Disable user account. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-disabling
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable own account"
        )
    
    user = await UserService.update_user(db, user_id, UserUpdate(disabled=True))
    return user

@router.post("/{user_id}/enable", response_model=UserResponse)
async def enable_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Enable user account. Admin only."""
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = await UserService.update_user(db, user_id, UserUpdate(disabled=False))
    return user