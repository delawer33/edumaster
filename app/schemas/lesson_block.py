from pydantic import BaseModel, HttpUrl, model_validator,field_serializer

from app.db import LessonBlockType


class TextContent(BaseModel):
    text: str

class UrlContent(BaseModel):
    url: HttpUrl

    @field_serializer('url')
    def serialize_url(self, url: HttpUrl) -> str:
        return str(url)

class ObjectContent(BaseModel):
    object_name: str
                

class SLessonBlockCreate(BaseModel):
    type: LessonBlockType
    content: TextContent | UrlContent | ObjectContent

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
    
    @field_serializer('content')
    def serialize_content(self, content: TextContent | UrlContent | ObjectContent) -> str:
        return content.model_dump_json() 


class SLessonBlockPatch(SLessonBlockCreate):
    pass


class SLessonBlockResponse(BaseModel):
    id: int
    lesson_id: int
    order: int
    type: LessonBlockType
    content: str
