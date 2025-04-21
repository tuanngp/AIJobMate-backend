from typing import Any, Optional, TypeVar, Dict, Generic
from pydantic import BaseModel

T = TypeVar("T")

class BaseResponseModel(BaseModel, Generic[T]):
    code: int
    message: str
    data: Optional[T] = None
    errors: Optional[Any] = None
    meta: Optional[Dict] = None 