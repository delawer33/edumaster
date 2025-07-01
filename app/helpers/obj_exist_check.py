from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Course, Module, Lesson, LessonBlock


async def course_exists(
        course_id: int,
        db: AsyncSession
):
    course = await db.scalar(
        select(Course).where(
            Course.id == course_id
        )
    )

    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден"
        )
    
    return course


async def module_exists(
        module_id: int,
        db: AsyncSession
):
    module = await db.scalar(
        select(Module).where(
            Module.id == module_id
        )
    )

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Модуль не найден"
        )

    return module


async def lesson_exists(
        lesson_id: int,
        db: AsyncSession
):
    lesson = await db.scalar(
        select(Lesson).where(
            Lesson.id == lesson_id
        ).options(
            selectinload(Lesson.module),
            selectinload(Lesson.blocks)
        )
    )

    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Урок не найден"
        )

    return lesson


async def lesson_block_exists(
        block_id: int,
        db: AsyncSession
):
    block = await db.scalar(
        select(LessonBlock).where(
            LessonBlock.id == block_id
        ).options(
            selectinload(LessonBlock.lesson)
        )
    )

    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Блок не найден"
        )

    return block

