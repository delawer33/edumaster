import datetime
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
import enum

from app.core import settings

ORDER_STEP = 100


class ObjectStatus(enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models"""

    type_annotation_map = {
        datetime.datetime: DateTime(timezone=True),
    }

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URL)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
