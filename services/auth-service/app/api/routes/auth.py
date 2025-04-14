from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Any
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.models.token import Token, RefreshToken
from app.models.user import UserCreate, UserResponse, User
from app.services.user_service import UserService
from app.services.token_service import TokenService
from app.db.database import get_db

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Register a new user."""
    # Check if user exists
    if await UserService.get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if await UserService.get_user_by_username(db, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    user = await UserService.create_user(db, user_in)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """Login for access token."""
    user = await UserService.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is disabled"
        )
    
    # Create tokens
    user_roles = [role.name for role in user.roles]
    access_token = create_access_token(
        user.id,
        user_roles
    )
    refresh_token = create_refresh_token(user.id, user_roles)
    
    # Store refresh token
    if not await TokenService.store_refresh_token(db, refresh_token, user.id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store refresh token"
        )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: RefreshToken,
    db: Session = Depends(get_db)
) -> Any:
    """Get new access token using refresh token."""
    try:
        payload = verify_token(refresh_token.refresh_token, "refresh")
        
        # Verify refresh token in storage
        if not await TokenService.verify_refresh_token(
            db, 
            refresh_token.refresh_token, 
            payload.sub
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user
        user = await UserService.get_user(db, payload.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is disabled"
            )
        
        # Create new tokens
        user_roles = [role.name for role in user.roles]
        new_access_token = create_access_token(
            user.id,
            user_roles
        )
        new_refresh_token = create_refresh_token(user.id, user_roles)
        
        # Revoke old refresh token and store new one
        await TokenService.revoke_refresh_token(db, refresh_token.refresh_token, payload.sub)
        if not await TokenService.store_refresh_token(db, new_refresh_token, user.id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not store refresh token"
            )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
@router.get("/verify")
async def verify_token_endpoint(request: Request) -> Any:
    """
    Verify token and return user info.
    This endpoint is used by API Gateway to verify tokens.
    """
    
    # Get authorization header
    auth_header = request.headers.get("authorization")
    
    try:
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header is missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization format. Use Bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Extract token
        token = auth_header.split(" ")[1]
        
        # Verify token
        token_data = verify_token(token, "access")
        
        # Return user info
        response = {
            "id": token_data.sub,
            "roles": token_data.roles,
            "exp": token_data.exp.timestamp(),
            "type": token_data.type
        }
        return response
        
    except ValueError as e:
        print(f"[ERROR] Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(
    refresh_token: RefreshToken,
    db: Session = Depends(get_db)
) -> Any:
    """Logout user by revoking refresh token."""
    try:
        payload = verify_token(refresh_token.refresh_token, "refresh")
        if await TokenService.revoke_refresh_token(db, refresh_token.refresh_token, payload.sub):
            return {"message": "Successfully logged out"}
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not revoke refresh token"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )