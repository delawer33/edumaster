from fastapi import (
    APIRouter, 
    HTTPException, 
    Response,
    status, 
    Depends,  
)
from collections import defaultdict
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.schemas import (
    SModuleCreate, 
    SModuleResponse, 
    SModuleTreeResponse,
    SModuleUpdate,
    SLessonResponse,
    build_module_tree_response
)

from app.db import User, get_async_db_session, Course, Module, ObjectStatus, Lesson, ModuleContentType
from app.dependencies.user import (
    get_current_user
)
from app.policies import CoursePolicy
from app.helpers.module_lesson import get_max_order, EntityType
from app.helpers import obj_exist_check, course_queries_utils


router = APIRouter(prefix='/course', tags=['Module'])


@router.get("/{course_id}/module/{module_id}", response_model=SModuleTreeResponse)
async def get_module_content(
    course_id: int,
    module_id: int,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
):
    
    course = await obj_exist_check.course_exists(course_id, db)
    module = await obj_exist_check.module_exists(module_id, db)
    
    await CoursePolicy.check_resource_access(current_user, module, "read", course)

    all_modules = await db.scalars(
        select(Module)
        .where(Module.course_id == module.course_id)
    )
    flat_modules = all_modules.unique().all()
    
    lessons = await db.scalars(
        select(Lesson)
        .where(Lesson.course_id == module.course_id)
        .order_by(Lesson.order)
    )
    all_lessons = lessons.unique().all()
    
    module_map = {m.id: {"module": m, "children": [], "lessons": []} for m in flat_modules}
    lessons_by_module = defaultdict(list)
    
    for lesson in all_lessons:
        lessons_by_module[lesson.module_id].append(lesson)
    
    root_module = None
    for module_data in flat_modules:
        node = module_map[module_data.id]
        
        node["lessons"] = lessons_by_module.get(module_data.id, [])
        
        if module_data.parent_module_id is None:
            if module_data.id == module_id:
                root_module = node
        else:
            parent_node = module_map.get(module_data.parent_module_id)
            if parent_node:
                parent_node["children"].append(node)
    
    if not root_module:
        root_module = module_map.get(module_id)
    
    if not root_module:
        raise HTTPException(404, "Структура модуля не найдена")    
    
    return build_module_tree_response(root_module)


@router.post("/{course_id}/module/", response_model=SModuleResponse)
async def create_module(
    course_id: int,
    module_data: SModuleCreate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
):

    data = module_data.model_dump()
    parent_module_id = data.get("parent_module_id")

    course = await obj_exist_check.course_exists(course_id, db)
    
    if parent_module_id is None:
        await CoursePolicy.check_resource_access(current_user, course, "write")
        lessons_in_course = await db.execute(
            select(Lesson).where(
                Lesson.course_id == course_id
            )
        )
        
        if lessons_in_course.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Курс может содержать только модули либо только уроки"
            )
        
        max_order = await get_max_order(
            db,
            EntityType.MODULE,
            course_id=course_id
        )
    else:
        parent = await obj_exist_check.module_exists(parent_module_id, db)

        await CoursePolicy.check_resource_access(current_user, parent, "write", course)

        if parent.content_type == ModuleContentType.lessons:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данный родительский модуль может содержать только уроки"
            )

        max_order = await get_max_order(
            db, 
            EntityType.MODULE,
            parent_module_id=parent_module_id
        )

        parent.content_type = ModuleContentType.modules

    try:
        print(parent_module_id)
        module = Module(
            **data,
            course_id=course_id,
            status=ObjectStatus.draft,
            order=max_order
        )

        if parent_module_id:
            db.add(parent)
        db.add(module)
        await db.commit()
        await db.refresh(module)
    
    except Exception as e:
        await db.rollback()
        # raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
    return module


@router.patch("/{course_id}/module/{module_id}")
async def patch_module(
    course_id: int,
    module_id: int,
    data: SModuleUpdate,
    db: AssertionError = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
):
    try:
        update_data = data.model_dump(exclude_unset=True)

        course = await obj_exist_check.course_exists(course_id, db)
        module = await obj_exist_check.module_exists(module_id, db)
            
        await CoursePolicy.check_resource_access(current_user, module, "write", course)

        is_archiving = update_data.get("status") == ObjectStatus.archived
        
        if is_archiving and module.status != ObjectStatus.archived:
            await course_queries_utils.archive_children(db, module_id=module_id)

        await db.execute(
            update(Module)
            .where(Module.id == module_id)
            .values(**update_data)
        )

        await db.commit()
        await db.refresh(module)

        return module
    
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{course_id}/module/{module_id}")
async def delete_module(
        course_id: int,
        module_id: int,
        db: AsyncSession = Depends(get_async_db_session),
        current_user: User = Depends(get_current_user)
):

    course = await obj_exist_check.course_exists(course_id, db)
    module = await obj_exist_check.module_exists(module_id, db)
        
    await CoursePolicy.check_single_course_access(course, current_user)
    await CoursePolicy.check_module_belongs_course(module, course)

    await db.delete(module)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

