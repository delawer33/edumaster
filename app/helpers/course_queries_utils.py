
from sqlalchemy import select, update, and_
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Module, Lesson, ObjectStatus

async def archive_module_tree(db: AsyncSession, module_id: int):
    # Создаем рекурсивный CTE для получения всех подмодулей
    modules = Module.__table__
    parent = aliased(modules, name="parent")
    child = aliased(modules, name="child")
    
    cte = (
        select(parent.c.id)
        .where(parent.c.id == module_id)
        .cte(recursive=True)
    )
    
    cte = cte.union_all(
        select(child.c.id)
        .select_from(child)
        .join(cte, child.c.parent_module_id == cte.c.id)
    )
    
    # Обновляем все модули в дереве
    await db.execute(
        update(Module)
        .where(Module.id.in_(select(cte.c.id)))
        .values(status=ObjectStatus.archived)
    )
    
    # Получаем ID всех модулей в дереве
    result = await db.execute(select(cte.c.id))
    module_ids = [row[0] for row in result]
    
    # Архивируем уроки во всех модулях дерева
    await db.execute(
        update(Lesson)
        .where(Lesson.module_id.in_(module_ids))
        .values(status=ObjectStatus.archived)
    )
    
    # Архивируем блоки уроков
    # await db.execute(
    #     update(LessonBlock)
    #     .where(LessonBlock.lesson_id.in_(
    #         select(Lesson.id).where(Lesson.module_id.in_(module_ids))
    #     ))
    #     .values(status=ObjectStatus.archived)
    # )
    
    await db.commit()


async def archive_children(
    db: AsyncSession,
    *,
    course_id: int | None = None,
    module_id: int | None = None
):
    if course_id:
        if course_id:
            # Архивируем все модули курса
            await db.execute(
                update(Module)
                .where(Module.course_id == course_id)
                .values(status=ObjectStatus.archived)
            )
            
            # Архивируем все уроки курса (включая корневые)
            await db.execute(
                update(Lesson)
                .where(Lesson.course_id == course_id)
                .values(status=ObjectStatus.archived)
            )
            
            # Архивируем все блоки уроков курса
            # await db.execute(
            #     update(LessonBlock)
            #     .where(LessonBlock.lesson_id.in_(
            #         select(Lesson.id).where(Lesson.course_id == course_id)
            #     ))
            #     .values(status=ObjectStatus.archived)
            # )
    elif module_id:
        await archive_module_tree(db, module_id)
