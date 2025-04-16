
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel


T = TypeVar("T")

class BaseResponseModel(BaseModel, Generic[T]):
    code: int
    message: str
    data: Optional[T] = None
    errors: Optional[Any] = None
    meta: Optional[dict] = None