from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from app.db import ObjectStatus
from .module import SArchivedModuleResponse, SArchivedLessonResponse


class SCourseBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    price: float = Field(..., gt=0)


class SCourseCreate(SCourseBase):
    pass


class SCourseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    status: Optional[ObjectStatus] = None
    model_config = ConfigDict(extra="forbid")


class SCourseResponse(SCourseBase):
    id: int
    owner_id: int
    status: ObjectStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SArchivedCourseResponse(BaseModel):
    id: int
    title: str
    type: str = "course"
    status: ObjectStatus
    modules: list[SArchivedModuleResponse] = []
    lessons: list[SArchivedLessonResponse] = []
    model_config = ConfigDict(from_attributes=True)