from pydantic import BaseModel, HttpUrl, model_validator

from app.db import LessonBlockType


class TextContent(BaseModel):
    text: str

class UrlContent(BaseModel):
    url: HttpUrl

class ObjectContent(BaseModel):
    object_name: str
                

class SLessonBlockCreate(BaseModel):
    type: LessonBlockType
    content: TextContent | UrlContent | ObjectContent
    module_id: int | None = None

    @model_validator(mode='after')
    def validate_content_type(self):
        content_type_map = {
            LessonBlockType.TEXT: TextContent,
            LessonBlockType.LINK: UrlContent,
            LessonBlockType.QUIZ: UrlContent,
            LessonBlockType.VIDEO: ObjectContent,
            LessonBlockType.AUDIO: ObjectContent,
            LessonBlockType.PDF: ObjectContent,
            LessonBlockType.IMAGE: ObjectContent
        }
        
        expected_type = content_type_map.get(self.type)
        if not isinstance(self.content, expected_type):
            raise ValueError(
                f"Несоответствие типов контента. Для {self.type} ожидался "
                f"{expected_type.__name__}, передано {type(self.content).__name__}"
            )
        return self


class SLessonBlockResponse(BaseModel):
    id: int
    lesson_id: int
    order: int
    type: LessonBlockType
    content: str
