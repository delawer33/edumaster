from fastapi import APIRouter

from .user import router as user_router
from .course import router as course_router
from .module import router as module_router
from .lesson import router as lesson_router
from .payments import router as payments_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(user_router)
v1_router.include_router(course_router)
v1_router.include_router(module_router)
v1_router.include_router(lesson_router)
v1_router.include_router(payments_router)
