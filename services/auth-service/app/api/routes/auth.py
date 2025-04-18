from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Any
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token
)

from app.schemas.base import BaseResponseModel
from app.schemas.token import TokenResponse, RefreshToken
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.services.token_service import TokenService
from app.db.database import get_db

router = APIRouter()

@router.post("/register", response_model=BaseResponseModel[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Register a new user."""
    try:
        # Check if user exists
        if await UserService.get_user_by_email(db, user_in.email):
            return BaseResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Email already registered",
                errors={"email": "Email already registered"}
            )
        
        if await UserService.get_user_by_username(db, user_in.username):
            return BaseResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Username already taken",
                errors={"username": "Username already taken"}
            )
        
        user = await UserService.create_user(db, user_in)
        return BaseResponseModel(
            code=status.HTTP_201_CREATED,
            message="User registered successfully",
            data=user,
            meta={
                "created_at": datetime.utcnow().timestamp()
            }
        )
    except ValueError as e:
        return BaseResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Error registering user",
            errors={"User": str(e)}
        )

@router.post("/login", response_model=BaseResponseModel[TokenResponse])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """Login for access token."""
    try:
        user = await UserService.authenticate(db, form_data.username, form_data.password)
        if not user:
            return BaseResponseModel(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Incorrect username or password",
                errors={"username": "Incorrect username or password"}
            )
        
        if user.disabled:
            return BaseResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="User account is disabled",
                errors={"username": "User account is disabled"}
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
            return BaseResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Could not store refresh token",
                errors={"refresh_token": "Could not store refresh token"}
            )
        
        return BaseResponseModel(
            code=status.HTTP_200_OK,
            message="Login successful",
            data=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer"
            ),
            meta={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "roles": user_roles
                },
                "expires_at": datetime.utcnow().timestamp() + 3600  # 1 hour expiration
            }
        )
    except (ValueError) as e:
        return BaseResponseModel(
            code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid credentials",
            errors={"credentials": str(e)}
        )
        
@router.post("/refresh", response_model=BaseResponseModel[TokenResponse])
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
            return BaseResponseModel(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token",
                errors={"refresh_token": "Invalid refresh token"}
            )
        
        # Get user
        user = await UserService.get_user(db, payload.sub)
        if not user:
            return BaseResponseModel(
                code=status.HTTP_404_NOT_FOUND,
                message="User not found",
                errors={"user": "User not found"}
            )
        
        if user.disabled:
            return BaseResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="User account is disabled",
                errors={"user": "User account is disabled"}
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
            return BaseResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Could not store new refresh token",
                errors={"refresh_token": "Could not store new refresh token"}
            )
        
        return BaseResponseModel(
            code=status.HTTP_200_OK,
            message="Token refreshed successfully",
            data=TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer"
            ),
            meta={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "roles": user_roles
                },
                "expires_at": datetime.utcnow().timestamp() + 3600
            }
        )
        
    except ValueError as e:
        return BaseResponseModel(
            code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid refresh token",
            errors={"refresh_token": str(e)}
        )

@router.get("/verify", response_model=BaseResponseModel[dict])
async def verify_token_endpoint(request: Request) -> Any:
    """
    Verify token and return user info.
    This endpoint is used by API Gateway to verify tokens.
    """
    
    # Get authorization header
    auth_header = request.headers.get("authorization")
    
    try:
        if not auth_header:
            return BaseResponseModel(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Authorization header is required",
                errors="Authorization header is required"
            )
            
        if not auth_header.startswith("Bearer "):
            return BaseResponseModel(
                code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid authorization format",
                errors="Invalid authorization format"
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
        return BaseResponseModel(
            code=status.HTTP_200_OK,
            message="Token verified successfully",
            data=response
        )
    except IndexError:
        return BaseResponseModel(
            code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid authorization format",
            errors="Invalid authorization format"
        )
    except HTTPException as e:
        return BaseResponseModel(
            code=e.status_code,
            message="Token verification failed",
            errors=str(e.detail)
        )
    except Exception as e:
        return BaseResponseModel(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Token verification failed",
            errors=str(e)
        )
    except ValueError as e:
        return BaseResponseModel(
            code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid token",
            errors=str(e)
        )

@router.post("/logout", response_model=BaseResponseModel[str])
async def logout(
    refresh_token: RefreshToken,
    db: Session = Depends(get_db)
) -> Any:
    """Logout user by revoking refresh token."""
    try:
        payload = verify_token(refresh_token.refresh_token, "refresh")
        if not await TokenService.revoke_refresh_token(db, refresh_token.refresh_token, payload.sub):
            return BaseResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Failed to revoke refresh token",
                errors={"refresh_token": "Failed to revoke refresh token"}
            )
        
        return BaseResponseModel(
                code=status.HTTP_200_OK,
                message="Logout successful",
                data="Refresh token revoked successfully"
            )
    except ValueError as e:
        return BaseResponseModel(
            code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid refresh token",
            errors={"refresh_token": str(e)}
        )