from datetime import datetime
from pydantic import BaseModel

# Pydantic models for request
class TokenPayload(BaseModel):
    sub: int  # user id
    exp: datetime
    iat: datetime
    type: str  # "access" or "refresh"
    roles: list[str]

class RefreshToken(BaseModel):
    refresh_token: str

# Pydantic models for response
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
