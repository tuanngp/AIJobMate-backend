from datetime import datetime, timedelta
from typing import Any, Optional, Union

from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from redis import Redis

from app.core.config import settings

# Constants
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client cho token blacklist
redis_client = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

# Mã hóa, xác minh password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Tạo access token
def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Tạo refresh token
def create_refresh_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Xác thực token
def verify_token(token: str, token_type: str = "access") -> dict:
    try:
        # Kiểm tra token trong blacklist
        if redis_client.get(f"blacklist:{token}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token đã bị vô hiệu hóa",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Giải mã và xác thực token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        
        # Kiểm tra loại token
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token không phải loại {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Thêm token vào blacklist
def blacklist_token(token: str, expire_in: int = None) -> None:
    """
    Thêm token vào blacklist
    
    Args:
        token: Token cần blacklist
        expire_in: Thời gian hết hạn (giây), mặc định là thời gian còn lại của token
    """
    try:
        # Giải mã token để lấy thời gian hết hạn
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        exp = payload.get("exp")
        
        # Tính thời gian còn lại của token
        if not expire_in and exp:
            now = datetime.utcnow().timestamp()
            expire_in = int(exp - now)
        
        # Thêm vào Redis với thời gian hết hạn
        if expire_in and expire_in > 0:
            redis_client.setex(f"blacklist:{token}", expire_in, "1")
        else:
            redis_client.set(f"blacklist:{token}", "1")
    except Exception as e:
        # Log lỗi nhưng không raise exception
        # Vì blacklist là tính năng phụ, không nên ảnh hưởng đến luồng chính
        print(f"Lỗi khi thêm token vào blacklist: {str(e)}")

# Xóa token khỏi blacklist
def remove_from_blacklist(token: str) -> None:
    """
    Xóa token khỏi blacklist
    """
    redis_client.delete(f"blacklist:{token}") 