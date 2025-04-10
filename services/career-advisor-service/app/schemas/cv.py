from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CVBase(BaseModel):
    file_name: str
    file_type: str


class CVCreate(CVBase):
    pass


class CVUpdate(CVBase):
    extracted_text: Optional[str] = None


class CVInDB(CVBase):
    id: int
    user_id: int
    original_content: str
    extracted_text: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CV(CVInDB):
    pass
