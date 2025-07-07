from datetime import datetime
from pydantic import BaseModel, ConfigDict

from .lesson_block import SLessonBlockResponse
from app.db import ObjectStatus


class SLessonBase(BaseModel):
    title: str
    summary: str
    duration: int


class SLessonResponse(SLessonBase):
    id: int
    order: int
    status: ObjectStatus
    module_id: int | None
    created_at: datetime
    updated_at: datetime


class SLessonFullReponse(SLessonResponse):
    blocks: list[SLessonBlockResponse] = []
    model_config = ConfigDict(from_attributes=True)


class SLessonCreate(SLessonBase):
    module_id: int | None = None
    model_config = ConfigDict(extra="forbid")


class SLessonUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    duration: int | None = None
    module_id: int | None = None
    status: ObjectStatus | None = None
    model_config = ConfigDict(extra="forbid")


class SArchivedLessonResponse(BaseModel):
    id: int
    title: str
    type: str = "lesson"
    status: ObjectStatus
    model_config = ConfigDict(from_attributes=True)
