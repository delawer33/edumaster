from fastapi import (
    APIRouter, 
    HTTPException, 
    status, 
    Depends,  
    Response
)
from datetime import timedelta
from collections import defaultdict
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from minio import Minio

from app.schemas import (
    SModuleCreate, 
    SModuleResponse, 
    SModuleTreeResponse,
    SModuleUpdate,
    SLessonResponse,
    SLessonFullReponse,
    SLessonCreate,
    SLessonUpdate,
    SLessonBlockResponse,
    SLessonBlockCreate,
    SLessonBlockPatch,
    build_module_tree_response
)

from app.helpers import obj_exist_check
from app.core import settings
from app.db import (
    User, 
    get_async_db_session, 
    Course, 
    Module, 
    ObjectStatus, 
    Lesson, 
    ModuleContentType,
    LessonBlock,
    LessonBlockType,
    
)
from app.dependencies.user import (
    get_current_user
)
from app.policies import CoursePolicy
from app.helpers.module_lesson import get_max_order, EntityType
from app.dependencies.minio import get_minio_client


router = APIRouter(prefix="/course", tags=["Lesson"])


@router.post("/{course_id}/lesson", response_model=SLessonResponse)
async def create_lesson(
        course_id: int,
        lesson_data: SLessonCreate,
        db: AsyncSession = Depends(get_async_db_session),
        current_user: User = Depends(get_current_user)
):
    
    data = lesson_data.model_dump()
    module_id = data.get("module_id")

    course = await obj_exist_check.course_exists(course_id, db)
    # await CoursePolicy.check_single_course_access(course, current_user)

    if not module_id:
        await CoursePolicy.check_resource_access(current_user, course, "write")

        modules_in_course = await db.execute(
            select(Module).where(
                Module.course_id == course_id
            )
        )
        
        if modules_in_course.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Курс может содержать только модули либо только уроки"
            )
        
        max_order = await get_max_order(
            db,
            EntityType.LESSON,
            course_id=course_id
        )

    else:
        module = await obj_exist_check.module_exists(module_id, db)
        
        await CoursePolicy.check_resource_access(current_user, module, "write", course)

        if module.content_type == ModuleContentType.modules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данный родительский модуль может содержать только курсы"
            )

        module.content_type = ModuleContentType.lessons

        max_order = await get_max_order(
            db,
            EntityType.LESSON,
            parent_module_id=module.id
        )

    try:
        lesson = Lesson(
            course_id=course_id,
            status=ObjectStatus.draft,
            order=max_order,
            **data
        )

        if module_id:
            db.add(module)
        db.add(lesson)
        await db.commit()
        await db.refresh(lesson)
    
        return lesson
    
    except Exception as e:
        await db.rollback()
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )  

@router.post("{course_id}/lesson/{lesson_id}/block", response_model=SLessonBlockResponse)
async def create_lesson_block(
    course_id: int,
    lesson_id: int,
    block_data: SLessonBlockCreate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
):
    lesson = await db.get(Lesson, lesson_id)
    
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    
    course = await obj_exist_check.course_exists(course_id, db)
    # try:
    #     module = await obj_exist_check.module_exists(module_id, db)
    # except HTTPException:
    #     module = None
    # except Exception as e:
    #     raise e

    await CoursePolicy.check_resource_access(current_user, lesson, "write", course)
    
    if block_data.type == LessonBlockType.TEXT:
        if not block_data.content.text:
            raise HTTPException(400, "Text content required")
        content_value = block_data.content.text
    
    elif block_data.type in [LessonBlockType.LINK, LessonBlockType.QUIZ]:
        if not block_data.content.url:
            raise HTTPException(400, "URL required")
        content_value = str(block_data.content.url)
    
    elif block_data.type in [LessonBlockType.VIDEO, LessonBlockType.AUDIO, 
                           LessonBlockType.IMAGE, LessonBlockType.PDF]:
        if not block_data.content.object_name:
            raise HTTPException(400, "File URL required")
        # TODO: check if url is minio url
        
        content_value = str(block_data.content.object_name)
    
    max_order = await get_max_order(
        db,
        EntityType.LESSON_BLOCK,
        lesson_id=lesson_id
    )

    block = LessonBlock(
        lesson_id=lesson_id,
        order=max_order,
        type=block_data.type,
        content=content_value
    )
    
    db.add(block)
    await db.commit()
    await db.refresh(block)
    
    return block


@router.get("/{course_id}/lesson/{lesson_id}", response_model=SLessonFullReponse)
async def get_lesson(
    course_id: int,
    lesson_id: int,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user),
    minio_client: Minio = Depends(get_minio_client)
):
    
    course = await obj_exist_check.course_exists(course_id, db)
    lesson = await obj_exist_check.lesson_exists(lesson_id, db)

    await CoursePolicy.check_resource_access(current_user, lesson, "read", course)
        
    for block in lesson.blocks:
        if block.type in [LessonBlockType.VIDEO, LessonBlockType.AUDIO, 
                          LessonBlockType.IMAGE, LessonBlockType.PDF]:
            if block.content:
                try:
                    object_name = block.content
                    
                    presigned_url = minio_client.presigned_get_object(
                        settings.MINIO_BUCKET,
                        object_name,
                        expires=timedelta(hours=1)
                    )
                    block.content = presigned_url
                except Exception as e:
                    # logger.error(f"Error generating presigned URL: {str(e)}")
                    print(e)
                    block.content = None

    lesson.blocks.sort(key=lambda x: x.order)
    
    return lesson


@router.patch("/{course_id}/lesson/{lesson_id}", response_model=SLessonResponse)
async def patch_lesson(
    course_id: int,
    lesson_id: int,
    lesson_data: SLessonUpdate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
):    
    data = lesson_data.model_dump(exclude_unset=True)
    
    module_id = data.get("module_id")

    course = await obj_exist_check.course_exists(course_id, db)
    lesson = await obj_exist_check.lesson_exists(lesson_id, db)

    await CoursePolicy.check_resource_access(current_user, lesson.module, "write", course)    

    if data.get("status") == ObjectStatus.published and lesson.module.status == ObjectStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Нельзя опубликовать урок, т.к. неопубликован модуль"
        )

    if module_id:
        new_module = await obj_exist_check.module_exists(module_id, db)
        if new_module.status == ObjectStatus.archived:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Модуль заархивирован"
            )
        await CoursePolicy.check_module_belongs_course(new_module, course)

        # Если урок опубликован, а модуль, в который его перемещают - в драфте
        if data.get("status") == ObjectStatus.published and new_module.status == ObjectStatus.draft:
            
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Нельзя переместить опубликованный урок в неопубликованный модуль"
            )
        
        if lesson.module_id is not None:
            module = await db.execute(
                select(Module).where(
                    Module.id == lesson.module_id
                ).options(
                    selectinload(Module.lessons)
                )
            )
            module = module.scalars().first()
            if len(module.lessons) == 1:
                module.content_type = ModuleContentType.empty

        if new_module.content_type == ModuleContentType.modules:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Модуль может состоять только из модулей, либо только из уроков"
            )
        elif new_module.content_type == ModuleContentType.empty:
            new_module.content_type = ModuleContentType.lessons
    
    try:
        for key, value in data.items():
            setattr(lesson, key, value)

        await db.commit()
        await db.refresh(lesson)

        return lesson
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    

@router.patch("/{course_id}/lesson/{lesson_id}/block/{block_id}", response_model=SLessonBlockResponse)
async def patch_lesson_block(
    course_id: int,
    lesson_id: int,
    block_id: int,
    block_data: SLessonBlockPatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    course = await obj_exist_check.course_exists(course_id, db)
    lesson = await obj_exist_check.lesson_exists(lesson_id, db)
    block = await obj_exist_check.lesson_block_exists(block_id, db)
    
    await CoursePolicy.check_resource_access(current_user, lesson, "write", course)

    data = block_data.model_dump(exclude_unset=True)

    try:
        for key, value in data.items():
            setattr(block, key, value)

        await db.commit()
        await db.refresh(block)

        return block
    
    except Exception as e:
        raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{course_id}/lesson/{lesson_id}")
async def delete_lesson(
    course_id: int,
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    course = await obj_exist_check.course_exists(course_id, db)
    lesson = await obj_exist_check.lesson_exists(lesson_id, db)

    await CoursePolicy.check_resource_access(current_user, lesson, "write", course)

    try:
        await db.delete(lesson)
        await db.commit()

    except SQLAlchemyError as e:
        await db.rollback()
        # logger.error(f"DB error deleting lesson {lesson_id}: {str(e)}")
        raise HTTPException(500, "Ошибка базы данных")
    
    except Exception as e:
        await db.rollback()
        # logger.critical(f"Unexpected error: {traceback.format_exc()}")
        raise HTTPException(500, "Internal server error")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

