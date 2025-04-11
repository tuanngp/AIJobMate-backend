from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.models.token import TokenPayload
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash from plain password."""
    return pwd_context.hash(password)

def create_token(subject: Union[str, Any], token_type: str, expires_delta: timedelta = None, roles: list[str] = None) -> str:
    """Create a JWT token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            if token_type == "access"
            else settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
        )
    
    to_encode = {
        "sub": str(subject),
        "type": token_type,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp(),
        "jti": str(uuid.uuid4()),
        "roles": roles or []
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY if token_type == "access" else settings.JWT_REFRESH_SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt
def verify_token(token: str, token_type: str) -> TokenPayload:
    """Verify and decode a JWT token."""
    try:
        secret_key = settings.JWT_SECRET_KEY if token_type == "access" else settings.JWT_REFRESH_SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        
        if payload["type"] != token_type:
            raise jwt.JWTError("Invalid token type")
        
        # Convert timestamps to datetime objects
        payload["exp"] = datetime.fromtimestamp(payload["exp"])
        payload["iat"] = datetime.fromtimestamp(payload["iat"])
            
        token_data = TokenPayload(**payload)
        
        if token_data.exp < datetime.utcnow():
            raise jwt.JWTError("Token has expired")
            
        return token_data
        return token_data
        
    except jwt.JWTError as e:
        raise ValueError(f"Could not validate credentials: {str(e)}")

def create_access_token(subject: Union[str, Any], roles: list[str]) -> str:
    """Create access token."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(subject, "access", expires_delta, roles)

def create_refresh_token(subject: Union[str, Any], roles: list[str]) -> str:
    """Create refresh token."""
    expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(subject, "refresh", expires_delta, roles)