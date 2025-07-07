from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FileCreateResponse(BaseModel):
    id: int
    original_name: str
    url: str
    uploaded_at: datetime


class LessonBlockCreate(BaseModel):
    lesson_id: int
    type: str
    content: Optional[str] = None
    file_id: Optional[int] = None
    order: int = Field(ge=0)

    class Config:
        use_enum_values = True
