from pydantic import BaseModel, HttpUrl, model_validator

from app.db import LessonBlockType


class BlockContent(BaseModel):
    text: str | None = None
    url: HttpUrl | None = None
    object_name: str | None = None
                

class SLessonBlockCreate(BaseModel):
    type: LessonBlockType
    content: BlockContent
    module_id: int | None = None

    @model_validator(mode="after")
    @classmethod
    def validate_content(cls, data):
        if isinstance(data, dict):
            typ = data.get("type")
            if typ == LessonBlockType.TEXT:
                if data.get("content") is not None \
                    or data.get("objectname") is not None:
                    
                    raise ValueError()

class SLessonBlockResponse(BaseModel):
    id: int
    lesson_id: int
    order: int
    type: LessonBlockType
    content: str
