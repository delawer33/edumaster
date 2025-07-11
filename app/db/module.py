import enum
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from app.db import Base, ObjectStatus


class ModuleContentType(enum.Enum):
    empty = "empty"
    modules = "modules"
    lessons = "lessons"


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id"),
        nullable=False,
    )
    parent_module_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("modules.id"),
        nullable=True,
    )
    status: Mapped[ObjectStatus] = mapped_column(
        Enum(ObjectStatus, name="course_status_enum"),
        nullable=False,
        default=ObjectStatus.draft,
        server_default="draft",
    )
    content_type: Mapped[ModuleContentType] = mapped_column(
        Enum(ModuleContentType, name="content_type_enum"),
        default=ModuleContentType.empty,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    course = relationship(
        "Course",
        back_populates="modules",
    )

    submodules: Mapped[List["Module"]] = relationship(
        "Module",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Module.order",
    )

    parent: Mapped[Optional["Module"]] = relationship(
        "Module",
        back_populates="submodules",
        remote_side=[id],
        lazy="joined",
    )

    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.order",
        lazy="raise",
    )

    @validates("submodules")
    def validate_submodules(self, key, module):
        if self.content_type == "lessons":
            raise ValueError("Parent module contains lessons")
        self.content_type = "modules"
        return module

    @validates("lessons")
    def validate_lessons(self, key, lesson):
        if self.content_type == "modules":
            raise ValueError("Parent module contains submodules")
        self.content_type = "lessons"
        return lesson

    def __repr__(self) -> str:
        return (
            f"<Module(id={self.id}, title={self.title}, "
            f"course_id={self.course_id}, parent_module_id={self.parent_module_id})>"
        )
