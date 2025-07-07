from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import (
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db import Base, ObjectStatus


class LessonBlockType(enum.Enum):
    TEXT = "text"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    PDF = "pdf"
    LINK = "link"
    QUIZ = "quiz"


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    duration: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    module_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("modules.id"),
        nullable=True,
    )

    course_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("courses.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    status: Mapped[ObjectStatus] = mapped_column(
        Enum(ObjectStatus, name="course_status_enum"),
        nullable=False,
        default=ObjectStatus.draft,
        server_default="draft",
    )

    module = relationship(
        "Module",
        back_populates="lessons",
    )

    course = relationship(
        "Course",
        back_populates="lessons",
    )

    blocks = relationship(
        "LessonBlock", back_populates="lesson", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Lesson(id={self.id}, title={self.title}), \
            order={self.order}, module_id={self.module_id}"


class LessonBlock(Base):
    __tablename__ = "lesson_blocks"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    lesson_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("lessons.id"),
        nullable=False,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    type: Mapped[LessonBlockType] = mapped_column(
        Enum(LessonBlockType),
        nullable=False,
    )

    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    lesson = relationship(
        "Lesson",
        back_populates="blocks",
    )

    def __repr__(self) -> str:
        return f"LessonBlock(id={self.id}, lesson_id={self.lesson_id}), \
            order={self.order}, type={self.type}"
