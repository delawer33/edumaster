from fastapi import (
    APIRouter, 
    HTTPException, 
    status, 
    Depends, 
    Query
)
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, or_, and_, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from app.schemas import (
    SCourseResponse, 
    SCourseCreate, 
    SCourseUpdate,
    SModuleTreeResponse,
    SLessonResponse,
    SArchivedCourseResponse,
    SArchivedLessonResponse,
    build_archived_module_tree,
    build_module_tree_response
)
from app.db import (
    get_async_db_session, 
    Course, 
    ObjectStatus,
    User,
    UserRole,
    Module,
    Lesson,
)
from app.dependencies import (
    get_current_user, 
    get_authorized_course, 
    get_current_user_teacher
)
from app.policies import CoursePolicy
from app.helpers import obj_exist_check, module_lesson as module_lesson_helpers, course_queries_utils

router = APIRouter(prefix="/course", tags=["Course"])


@router.get("/{course_id}/content/", response_model=list[SModuleTreeResponse | SLessonResponse])
async def get_course_content(
    course_id: int,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user)
):
    
    course = await obj_exist_check.course_exists(course_id, db)
    
    await CoursePolicy.check_resource_access(current_user, course, "read")

    is_admin = current_user.role == UserRole.admin
    is_teacher = (course.owner_id == current_user.id)

    module_query = select(Module).where(Module.course_id == course_id)

    if is_teacher:
        module_query = module_query.where(Module.status != ObjectStatus.archived)
    elif not is_admin:
        module_query = module_query.where(Module.status == ObjectStatus.published)
    
    result = await db.execute(
        module_query.options(
            selectinload(Module.submodules),
            selectinload(Module.lessons)
        )
    )
    flat_modules = result.unique().scalars().all()

    response_items = []

    if flat_modules:
        module_map: dict[int, dict] = {}
        
        for module in flat_modules:
            lessons = module.lessons
            if is_admin:
                lessons = [lesson for lesson in lessons]
            elif is_teacher:
                lessons = [lesson for lesson in lessons if lesson.status != ObjectStatus.archived]
            else:
                lessons = [lesson for lesson in lessons if lesson.status == ObjectStatus.published]
            
            module_map[module.id] = {
                "module": module,
                "children": [],
                "lessons": lessons
            }
        
        root_nodes = []
        for module in flat_modules:
            node = module_map[module.id]
            
            # if not is_admin and not is_teacher and module.status != ObjectStatus.published:
            #     continue
            # if is_teacher and module.status == ObjectStatus.archived:
            #     continue
                
            if module.parent_module_id is None:
                root_nodes.append(node)
            else:
                parent_node = module_map.get(module.parent_module_id)
                if parent_node:
                    parent_node["children"].append(node)
        
        for node in module_map.values():
            node["children"].sort(key=lambda x: x["module"].order)
            node["lessons"].sort(key=lambda x: x.order)
        
        for node in root_nodes:
            # if not is_teacher_or_admin and node["module"].status != ObjectStatus.published:
            #     continue
            response_items.append(build_module_tree_response(node))
    
    return response_items


@router.post(
    "/", 
    response_model=SCourseResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_course(
    course_data: SCourseCreate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user = Depends(get_current_user_teacher)
):
    async with db.begin():
        new_course = Course(
            **course_data.model_dump(),
            status=ObjectStatus.draft,
            owner_id=current_user.id
        )

        db.add(new_course)
        await db.flush()
        await db.refresh(new_course)
  
    return new_course


@router.patch("/{course_id}", response_model=SCourseResponse)
async def patch_course(
    course_id: int,
    update_data: SCourseUpdate,
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user_teacher),
):
    try:
        
        course = await obj_exist_check.course_exists(course_id, db)

        await CoursePolicy.check_resource_access(current_user, course, "read")
        
        update_values = update_data.model_dump(exclude_unset=True)

        is_archiving = update_values.get("status") == ObjectStatus.archived

        if is_archiving and course.status != ObjectStatus.archived:
            print("!!!")
            await course_queries_utils.archive_children(db, course_id=course_id)

        await db.execute(
            update(Course)
            .where(Course.id == course.id)
            .values(**update_values)
        )

        await db.commit()
        await db.refresh(course)

        return course
    
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )

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


@router.get("/", response_model=list[SCourseResponse])
async def get_courses(
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    search: Optional[str] = Query(None, min_length=2, max_length=50),
    owner_username: Optional[str] = Query(None),
    status: Optional[ObjectStatus] = Query(None)
):
    try:
        query = select(Course).where(
            CoursePolicy.build_access_condition(current_user)
        ).order_by(Course.created_at.desc())

        filters = []

        if search:
            filters.append(or_(
                Course.title.ilike(f"%{search}%"),
                Course.description.ilike(f"%{search}%")
            ))

        if owner_username:
            owner = await db.execute(
                select(User).where(User.username == owner_username)
            )
            owner = owner.scalars().first()
            if not owner:
                raise HTTPException(404, "User not found")
            filters.append(Course.owner_id == owner.id)

        if status:
            if current_user.role == UserRole.admin:
                filters.append(Course.status == status)
            else:
                allowed_statuses = CoursePolicy.allowed_statuses(current_user)
                if status not in allowed_statuses:
                    raise HTTPException(403, "Forbidden status filter")
                filters.append(Course.status == status)

        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(
            query.offset(skip)
            .limit(limit)
            .options(selectinload(Course.owner))
        )
        
        return result.scalars().all()

    except HTTPException as he:
        raise he
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server Error"
        )
    

@router.get("/my", response_model=list[SCourseResponse])
async def get_teacher_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    search: Optional[str] = Query(None, min_length=2, max_length=50),
    status: Optional[ObjectStatus] = Query(None),
    current_user: User = Depends(get_current_user_teacher),
    db: AsyncSession = Depends(get_async_db_session)
):
    try:
        query = select(Course).where(
            and_(Course.owner_id == current_user.id, Course.status != ObjectStatus.archived)
        ).order_by(Course.created_at.desc())

        filters = []

        if search:
            filters.append(or_(
                Course.title.ilike(f"%{search}%"),
                Course.description.ilike(f"%{search}%")
            ))

        if status:
            filters.append(Course.status == status)

        if filters:
            query = query.where(and_(*filters))

        result = await db.execute(
            query.offset(skip)
            .limit(limit)
            .options(selectinload(Course.owner))
        )
        
        return result.scalars().all()

    except HTTPException as he:
        raise he
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server Error"
        )


# @router.get("/{couse_id}", response_model=SCourseResponse)
# async def get_course(
#     course: Course = Depends(get_authorized_course)
# ):
#     return course


@router.get("/archived/", response_model=list[SArchivedCourseResponse])
async def get_archived_content_tree(
    db: AsyncSession = Depends(get_async_db_session),
    current_user: User = Depends(get_current_user_teacher)
):
    courses_query = select(Course).where(
        Course.status == ObjectStatus.archived
    ).options(
        selectinload(Course.modules).selectinload(Module.submodules),
        selectinload(Course.modules).selectinload(Module.lessons),
        selectinload(Course.lessons)
    )
    
    courses_query = courses_query.where(Course.owner_id == current_user.id)
    
    result = await db.execute(courses_query)
    archived_courses = result.scalars().all()
    
    non_archived_courses_with_archived_content = await get_non_archived_courses_with_archived_content(db, current_user)
    
    all_courses = list(archived_courses) + list(non_archived_courses_with_archived_content)
    
    response = []
    for course in all_courses:
        course_data = SArchivedCourseResponse(
            id=course.id,
            title=course.title,
            status=course.status
            # archived_at=course.updated_at
        )
        
        if hasattr(course, 'modules'):
            all_modules = []
            for module in course.modules:
                all_modules.extend(module_lesson_helpers.get_all_submodules(module))
            
            archived_modules = [m for m in all_modules if m.status == ObjectStatus.archived]
            
            module_map = {m.id: m for m in archived_modules}
            root_modules = [m for m in archived_modules 
                            if m.parent_module_id is None or m.parent_module_id not in module_map]
            
            for module in root_modules:
                module_node = build_archived_module_tree(module, module_map, course)
                course_data.modules.append(module_node)
        
        # Обработка уроков
        if hasattr(course, 'lessons'):
            # Уроки в корне курса
            course_data.lessons = [
                SArchivedLessonResponse(
                    id=lesson.id,
                    title=lesson.title,
                    status=lesson.status,
                    archived_at=lesson.updated_at
                )
                for lesson in course.lessons 
                if lesson.status == ObjectStatus.archived and lesson.module_id is None
            ]
            
            # Уроки в модулях (уже обработаны в build_module_tree)
        
        response.append(course_data)
    
    return response

async def get_non_archived_courses_with_archived_content(
    db: AsyncSession,
    current_user: User
) -> List[Course]:
    """
    Возвращает незаархивированные курсы, содержащие заархивированные модули или уроки
    """
    # Подзапрос для архивных модулей
    archived_modules_subquery = exists().where(
        (Module.course_id == Course.id) &
        (Module.status == ObjectStatus.archived)
    )
    
    # Подзапрос для архивных уроков
    archived_lessons_subquery = exists().where(
        (Lesson.course_id == Course.id) &
        (Lesson.status == ObjectStatus.archived)
    )
    
    # Основной запрос
    course_ids_query = select(Course.id).distinct().where(
        Course.status != ObjectStatus.archived
    ).where(
        or_(
            archived_modules_subquery,
            archived_lessons_subquery
        )
    )
    
    if current_user.role == UserRole.teacher:
        course_ids_query = course_ids_query.where(Course.owner_id == current_user.id)
    
    result = await db.execute(course_ids_query)
    course_ids = [row[0] for row in result]
    
    if not course_ids:
        return []
    
    # Загружаем курсы с полной структурой
    courses_query = select(Course).where(
        Course.id.in_(course_ids)
    ).options(
        selectinload(Course.modules).selectinload(Module.submodules),
        selectinload(Course.modules).selectinload(Module.lessons),
        selectinload(Course.lessons)
    )
    
    result = await db.execute(courses_query)
    return result.scalars().all()