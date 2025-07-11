from sqlalchemy import Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import ENUM as Enum
from datetime import datetime, timezone

from app.db import Base, ObjectStatus


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ObjectStatus] = mapped_column(
        Enum(ObjectStatus, name="course_status_enum"),
        nullable=False,
        default=ObjectStatus.draft,
        server_default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    owner = relationship("User", back_populates="courses")

    modules = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    lessons = relationship(
        "Lesson",
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    students = relationship(
        "User",
        secondary="user_course",
        back_populates="courses",
        lazy="selectin",
    )

    purchases = relationship("CoursePurchase", back_populates="course")
