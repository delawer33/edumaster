from sqlalchemy import select, update, or_, exists
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Module, Lesson, ObjectStatus, User, Course, UserRole


async def archive_module_tree(db: AsyncSession, module_id: int):
    modules = Module.__table__
    parent = aliased(modules, name="parent")
    child = aliased(modules, name="child")

    cte = (
        select(parent.c.id).where(parent.c.id == module_id).cte(recursive=True)
    )

    cte = cte.union_all(
        select(child.c.id)
        .select_from(child)
        .join(cte, child.c.parent_module_id == cte.c.id)
    )

    await db.execute(
        update(Module)
        .where(Module.id.in_(select(cte.c.id)))
        .values(status=ObjectStatus.archived)
    )

    result = await db.execute(select(cte.c.id))
    module_ids = [row[0] for row in result]

    await db.execute(
        update(Lesson)
        .where(Lesson.module_id.in_(module_ids))
        .values(status=ObjectStatus.archived)
    )

    await db.commit()


async def archive_children(
    db: AsyncSession,
    *,
    course_id: int | None = None,
    module_id: int | None = None
):
    if course_id:
        if course_id:
            await db.execute(
                update(Module)
                .where(Module.course_id == course_id)
                .values(status=ObjectStatus.archived)
            )

            await db.execute(
                update(Lesson)
                .where(Lesson.course_id == course_id)
                .values(status=ObjectStatus.archived)
            )
    elif module_id:
        await archive_module_tree(db, module_id)


async def get_non_archived_courses_with_archived_content(
    db: AsyncSession, current_user: User
) -> list[Course]:
    archived_modules_subquery = exists().where(
        (Module.course_id == Course.id)
        & (Module.status == ObjectStatus.archived)
    )

    archived_lessons_subquery = exists().where(
        (Lesson.course_id == Course.id)
        & (Lesson.status == ObjectStatus.archived)
    )

    course_ids_query = (
        select(Course.id)
        .distinct()
        .where(Course.status != ObjectStatus.archived)
        .where(or_(archived_modules_subquery, archived_lessons_subquery))
    )

    if current_user.role == UserRole.teacher:
        course_ids_query = course_ids_query.where(
            Course.owner_id == current_user.id
        )

    result = await db.execute(course_ids_query)
    course_ids = [row[0] for row in result]

    if not course_ids:
        return []

    courses_query = (
        select(Course)
        .where(Course.id.in_(course_ids))
        .options(
            selectinload(Course.lessons),
            selectinload(Course.modules).selectinload(Module.submodules),
            selectinload(Course.modules).selectinload(Module.lessons),
        )
    )

    result = await db.execute(courses_query)
    courses = result.scalars().all()

    return courses
