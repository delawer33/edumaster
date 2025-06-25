from fastapi import Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_current_user
from app.policies import CoursePolicy
from app.db import get_async_db_session, User, Course


async def get_authorized_course(
    course_id: int,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
) -> Course:
    
    query = select(Course).where(
        Course.id == course_id,
        CoursePolicy.build_access_condition(current_user)
    )
    
    result = await db.execute(query)
    course = result.scalars().first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Курс не найден или доступ запрещен"
        )
    
    return course