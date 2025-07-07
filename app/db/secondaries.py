from sqlalchemy import Table, Column, Integer, ForeignKey, DateTime, Float

from .base import Base

user_course = Table(
    "user_course",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
    Column("enrolled_at", DateTime, nullable=False),
    Column("progress", Float, default=0.0, nullable=False),
)
