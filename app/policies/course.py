from fastapi import HTTPException, status
from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import User, Course, UserRole, ObjectStatus, Module, Lesson

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
        user: User,
        resource: Course | Module | Lesson,
        action: str,  # "read" или "write"
        preloaded_course: Course | None = None
    ):
        """
        Проверяет доступ пользователя к ресурсу без дополнительных запросов к БД
        """
        # Админам разрешаем все действия
        if user.role == UserRole.admin:
            return True

        # Определяем связанные объекты
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

        # Проверяем доступ к курсу
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Курс не найден"
            )

        # Учитель может работать только со своими курсами
        is_owner = user.role == UserRole.teacher and course.owner_id == user.id

        # Запись (изменение) разрешена только владельцу/админу
        if action == "write":
            # Заархивированные курсы нельзя изменять
            if course.status == ObjectStatus.archived:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Курс заархивирован, изменения запрещены"
                )
            
            # Учитель может изменять только свои неархивные курсы
            if not is_owner:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для изменения"
                )
            
            # Дополнительные проверки для модулей/уроков
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

        # Чтение разрешено:
        if action == "read":
            # Для учителей/админов разрешаем чтение в любом статусе
            if is_owner or user.role == UserRole.admin:
                return True
            
            # Для обычных пользователей:
            # 1. Курс должен быть опубликован
            if course.status != ObjectStatus.published:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Курс не опубликован"
                )
            
            # 2. Модуль должен быть опубликован (если есть)
            if module and module.status != ObjectStatus.published:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Модуль не опубликован"
                )
            
            # 3. Урок должен быть опубликован
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
