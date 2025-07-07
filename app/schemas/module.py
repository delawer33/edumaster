from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from app.db import ObjectStatus

from .lesson import SLessonResponse, SArchivedLessonResponse


class SModuleBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str


class SModuleCreate(SModuleBase):
    parent_module_id: int | None = None


class SModuleUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[ObjectStatus] = None
    model_config = ConfigDict(extra="forbid")


class SModuleResponse(SModuleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    status: str
    order: int
    course_id: int = None
    parent_module_id: int | None = None
    content_type: str
    content: list["SModuleResponse"] | list[SLessonResponse] = []
    # lessons: List[LessonResponse] = []
    model_config = ConfigDict(from_attributes=True)


class SModuleTreeResponse(SModuleResponse):
    pass


class SArchivedModuleResponse(BaseModel):
    id: int
    title: str
    # archived_at: datetime
    type: str = "module"
    status: ObjectStatus
    children: list["SArchivedModuleResponse"] = []
    lessons: list["SArchivedLessonResponse"] = []
    model_config = ConfigDict(from_attributes=True)
