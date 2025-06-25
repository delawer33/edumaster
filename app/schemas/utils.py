from app.db import Module, Lesson, ModuleContentType, Course, ObjectStatus

from .lesson import SArchivedLessonResponse, SLessonResponse
from .module import SArchivedModuleResponse, SModuleTreeResponse

def build_archived_module_tree(
    module: Module,
    module_map: dict[int, Module],
    course: Course
) -> SArchivedModuleResponse:
    node = SArchivedModuleResponse(
        id=module.id,
        title=module.title,
        status=module.status,
        archived_at=module.updated_at
    )
    
    node.lessons = [
        SArchivedLessonResponse(
            id=lesson.id,
            title=lesson.title,
            status=lesson.status,
            archived_at=lesson.updated_at
        )
        for lesson in module.lessons
        if lesson.status == ObjectStatus.archived
    ]
    
    for submodule in module.submodules:
        if submodule.id in module_map:
            child_node = build_archived_module_tree(submodule, module_map, course)
            node.children.append(child_node)
    
    return node


def build_module_tree_response(node):
        module = node["module"]
        
        return SModuleTreeResponse(
            id=module.id,
            title=module.title,
            description=module.description,
            order=module.order,
            status=module.status,
            created_at=module.created_at,
            updated_at=module.updated_at,
            course_id=module.course_id,
            parent_module_id=module.parent_module_id,
            content_type=module.content_type,
            content=(
                [build_module_tree_response(child) for child in node["children"]] 
                if module.content_type == ModuleContentType.modules 
                else [
                    SLessonResponse(
                        id=lesson.id,
                        title=lesson.title,
                        summary=lesson.summary,
                        duration=lesson.duration,
                        module_id=lesson.module_id,
                        order=lesson.order,
                        status=lesson.status,
                        created_at=lesson.created_at,
                        updated_at=lesson.updated_at
                    ) for lesson in node["lessons"]
                ]
            )
        )

