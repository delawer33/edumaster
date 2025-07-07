from fastapi import HTTPException, status
from sqlalchemy import or_, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import User, Course, UserRole, ObjectStatus, Module, Lesson, CoursePurchase


class CoursePolicy:
    @classmethod
    def build_access_condition(cls, user: User):
        if user.role == UserRole.admin:
            return True
        
        if user.role == UserRole.teacher:
            return or_(
                Course.status == ObjectStatus.published,
                and_(
                    Course.owner_id == user.id,
                    Course.status.in_([
                        ObjectStatus.draft,
                        ObjectStatus.archived
                    ])
                )
            )
        
        return Course.status == ObjectStatus.published


    @classmethod
    async def check_course_archived(
        cls,
        course: Course
    ):
        if course.status == ObjectStatus.archived:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Курс заархивирован"
            )

    @classmethod
    async def check_single_course_access(
        cls,
        course: Course,
        user: User
    ):
        cls.check_course_archived(course)        

        if user.role == UserRole.admin:
            return
        
        if course.status == ObjectStatus.published:
            return
        
        if user.role == UserRole.teacher and course.owner_id == user.id:
            return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ отклонен"
        )
    
    @classmethod
    async def check_module_belongs_course(
        cls,
        module: Module,
        course: Course
    ):
        if module.course_id == course.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Курс не принадлежит модулю"
        )
    
    @classmethod
    async def check_lesson_belongs_course(
        cls,
        lesson: Lesson,
        course: Course
    ):
        if lesson.course_id == course.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Урок не принадлежит курсу"
        )
    
    
    @classmethod
    async def check_lesson_belongs_module(
        cls,
        lesson: Lesson,
        module: Module
    ):
        if lesson.module_id == module.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Урок не принадлежит модулю"
        )
    
    @classmethod
    async def check_resource_access(
        cls,
        db: AsyncSession,
        user: User,
        resource: Course | Module | Lesson,
        action: str,  # "read" или "write"
        preloaded_course: Course | None = None,
    ):
        if user.role == UserRole.admin:
            return True

        course = None
        module = None
        print(type(resource))
        
        if isinstance(resource, Course):
            course = resource
        elif isinstance(resource, Module):
            course = preloaded_course or resource.course
            module = resource
        elif isinstance(resource, Lesson):
            course = preloaded_course or resource.course
            module = resource.module if hasattr(resource, 'module') else None
        else:
            raise ValueError("Неподдерживаемый тип ресурса")

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Курс не найден"
            )

        is_owner = user.role == UserRole.teacher and course.owner_id == user.id

        if action == "write":
            if course.status == ObjectStatus.archived:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Курс заархивирован, изменения запрещены"
                )
            
            if not is_owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для изменения"
                )
            
            if isinstance(resource, Module) and resource.status == ObjectStatus.archived:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Модуль заархивирован, изменения запрещены"
                )
            
            if isinstance(resource, Lesson) and resource.status == ObjectStatus.archived:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Урок заархивирован, изменения запрещены"
                )
            
            return True

        if action == "read":
            if is_owner or user.role == UserRole.admin:
                return True

            stmt = select(CoursePurchase).where(
                CoursePurchase.user_id == user.id
            )

            cp = await db.execute(stmt)

            cp = cp.scalars().first()
            if cp is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Курс не приобретен"
                )
                    
            if course.status != ObjectStatus.published:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Курс не опубликован"
                )
            
            if module and module.status != ObjectStatus.published:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Модуль не опубликован"
                )
            
            if isinstance(resource, Lesson) and resource.status != ObjectStatus.published:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Урок не опубликован"
                )
            
            return True

        raise ValueError("Неподдерживаемое действие")
        
    
    @classmethod
    def allowed_statuses(cls, user: User) -> list:
        statuses = [ObjectStatus.published]
        if user.role == UserRole.admin:
            statuses = list(ObjectStatus)
        # elif user.role == UserRole.teacher:
        #     statuses.extend([CourseStatus.draft, CourseStatus.archived])
        return statuses
