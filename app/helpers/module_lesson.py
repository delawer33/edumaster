from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from enum import Enum

from app.db import Module, Lesson, LessonBlock, ORDER_STEP


class EntityType(Enum):
    MODULE = "module"
    LESSON = "lesson"
    LESSON_BLOCK = "lesson_block"


async def get_max_order(
    db: AsyncSession,
    entity_type: EntityType,
    *,
    course_id: int | None = None,
    parent_module_id: int | None = None,
    lesson_id: int | None = None
):

    if entity_type == EntityType.MODULE:
        if parent_module_id:
            condition = Module.parent_module_id == parent_module_id
        elif course_id:
            condition = Module.course_id == course_id
        else:
            raise ValueError(
                "Для модуля требуется course_id или parent_module_id"
            )
        model = Module

    elif entity_type == EntityType.LESSON:
        if (
            not parent_module_id
            and not course_id
            or parent_module_id
            and course_id
        ):
            raise ValueError(
                "Для урока требуется parent_module_id (ID модуля) или course_id (ID курса)"
            )
        if parent_module_id:
            condition = Lesson.module_id == parent_module_id
        elif course_id:
            condition = Lesson.course_id == course_id

        model = Lesson

    elif entity_type == EntityType.LESSON_BLOCK:
        if not lesson_id:
            raise ValueError("Для блока урока требуется lesson_id")
        condition = LessonBlock.lesson_id == lesson_id
        model = LessonBlock

    stmt = select(func.max(model.order)).where(condition)
    result = await db.execute(stmt)
    max_order = result.scalar() or 0

    return max_order + ORDER_STEP


def get_all_submodules(module: Module) -> Module | None:
    modules = [module]
    for submodule in module.submodules:
        modules.extend(get_all_submodules(submodule))
    return modules


# async def auto_set_order(
#     target: Module | Lesson,
#     db: AsyncSession
# ):
#     parent = target.parent if isinstance(target, Module) else target.module

#     if target.order == 0:
#         target.order = await get_max_order(db, parent, isinstance(target, Module))
#     else:
#         await shift_orders(
#             ...
#         )


# async def shift_orders(
#     db: AsyncSession,
#     parent: Module | None,
#     target_order: int,
#     is_module: bool
# ):
#     table = Module.__table__ if is_module else Lesson.__table__

#     overlapping = await db.execute(
#         select(table).where(
#             table.c.order == target_order,
#             table.c.parent_id == (parent.id if parent else None)
#         )
#     )
#     overlapping = overlapping.scalars().first()

#     if not overlapping:
#         return

#     min_order = min(item.order for item in overlapping)
#     shift = (min_order // ORDER_STEP) * ORDER_STEP + ORDER_STEP


async def recalculate_orders(session: AsyncSession, ordered_ids: list[int]):
    current_positions = {id: idx for idx, id in enumerate(ordered_ids, 1)}

    modules = await session.scalars(
        select(Module).where(Module.id.in_(ordered_ids))
    )

    for module in modules:
        new_order = current_positions[module.id] * ORDER_STEP
        if module.order != new_order:
            module.order = new_order

    await session.commit()
