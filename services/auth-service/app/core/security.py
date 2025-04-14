from datetime import datetime, timedelta, timezone
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
    current_time = datetime.now(timezone.utc)
    
    if expires_delta:
        expire = current_time + expires_delta
    else:
        expire_minutes = (settings.ACCESS_TOKEN_EXPIRE_MINUTES if token_type == "access"
                       else settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
        expire = current_time + timedelta(minutes=expire_minutes)
    
    to_encode = {
        "sub": str(subject),
        "type": token_type,
        "exp": expire.timestamp(),
        "iat": current_time.timestamp(),
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
        current_time = datetime.now(timezone.utc)
        
        secret_key = settings.JWT_SECRET_KEY if token_type == "access" else settings.JWT_REFRESH_SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        
        if payload["type"] != token_type:
            raise jwt.JWTError("Invalid token type")
        
        # Convert timestamps to datetime objects
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        payload["exp"] = exp_time
        payload["iat"] = iat_time
            
        token_data = TokenPayload(**payload)
        
        if token_data.exp < current_time:
            time_diff = current_time - token_data.exp
            raise jwt.JWTError("Token has expired")
            
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