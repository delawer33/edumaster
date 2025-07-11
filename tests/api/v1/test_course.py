# tests/api/v1/test_course.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.db import ObjectStatus
from app.db.user import User, UserRole
from app.db.course import Course
from app.db.module import Module
from app.db.lesson import Lesson

from app.app import app


@pytest.mark.asyncio
async def test_get_course_content_as_owner_teacher(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_course: Course,
    test_draft_module: Module,
    test_archived_module: Module,
    test_lesson: Lesson,
    override_get_current_user_teacher,
):
    test_draft_module.course_id = test_course.id
    test_archived_module.course_id = test_course.id
    test_lesson.course_id = test_course.id
    test_lesson.module_id = test_draft_module.id
    await test_db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"api/v1/course/{test_course.id}/content/")
    assert response.status_code == 200

    module_titles = [item.get("title") for item in response.json()]
    for module in response.json():
        if module.get("id") == test_draft_module.id:
            assert test_lesson.title == module.get("content")[0].get("title")

    assert test_draft_module.title in module_titles
    assert test_archived_module.title not in module_titles


@pytest.mark.asyncio
async def test_get_course_content_as_student_purchased(
    test_db: AsyncSession,
    test_user: User,
    test_course: Course,
    test_draft_module: Module,
    test_archived_module: Module,
    test_lesson: Lesson,
    test_course_purchase,
    override_get_current_user_student,
):
    test_draft_module.course_id = test_course.id
    test_archived_module.course_id = test_course.id
    test_lesson.course_id = test_course.id
    test_lesson.module_id = test_draft_module.id
    await test_db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/course/{test_course.id}/content/")
    assert response.status_code == 200

    content_titles = [item.get("title") for item in response.json()]

    assert test_lesson.title not in content_titles
    assert test_draft_module.title not in content_titles
    assert test_archived_module.title not in content_titles


@pytest.mark.asyncio
async def test_get_course_content_as_student_not_purchased(
    test_db: AsyncSession,
    test_user: User,
    test_course: Course,
    override_get_current_user_student,
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/course/{test_course.id}/content/")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_course_as_teacher(
    test_db: AsyncSession,
    test_teacher_user: User,
    override_get_current_user_teacher,
):
    course_data = {
        "title": "New Course by Teacher",
        "description": "Description for new course",
        "price": 1000,
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/course/", json=course_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Course by Teacher"
    assert data["owner_id"] == test_teacher_user.id
    assert data["status"] == ObjectStatus.draft.value


@pytest.mark.asyncio
async def test_create_course_as_student_forbidden(
    test_db: AsyncSession, test_user: User, override_get_current_user_student
):
    course_data = {
        "title": "Course by Student",
        "description": "Should be forbidden",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/api/v1/course/", json=course_data)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_course_as_owner_teacher(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_draft_course: Course,
    override_get_current_user_teacher,
):
    patch_data = {
        "title": "Updated Title",
        "status": ObjectStatus.published.value,
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/course/{test_draft_course.id}", json=patch_data
        )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == ObjectStatus.published.value


@pytest.mark.asyncio
async def test_patch_course_archive_status_archives_children(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_course: Course,
    test_module: Module,
    test_lesson: Lesson,
    override_get_current_user_teacher,
):
    test_module.course_id = test_course.id
    test_lesson.course_id = test_course.id
    test_lesson.module_id = test_module.id
    await test_db.commit()

    patch_data = {"status": ObjectStatus.archived.value}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/course/{test_course.id}", json=patch_data
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == ObjectStatus.archived.value

    await test_db.refresh(test_module)
    await test_db.refresh(test_lesson)
    assert test_module.status == ObjectStatus.archived
    assert test_lesson.status == ObjectStatus.archived


@pytest.mark.asyncio
async def test_patch_course_as_non_owner_teacher_forbidden(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_another_teacher_user: User,
    override_get_current_user_teacher,
):
    course_by_another_teacher = Course(
        title="Another Teacher's Course",
        description="Owned by another teacher",
        status=ObjectStatus.draft,
        owner_id=test_another_teacher_user.id,
        price=1000,
    )
    test_db.add(course_by_another_teacher)
    await test_db.flush()
    await test_db.refresh(course_by_another_teacher)

    patch_data = {"title": "Attempt to patch"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/course/{course_by_another_teacher.id}", json=patch_data
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_archived_course_forbidden(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_archived_course: Course,
    override_get_current_user_teacher,
):
    patch_data = {"title": "New Title for Archived"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/course/{test_archived_course.id}", json=patch_data
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_courses_as_admin(
    test_db: AsyncSession,
    test_admin_user: User,
    test_course: Course,
    test_draft_course: Course,
    test_archived_course: Course,
    override_get_current_user_admin,
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/")
    assert response.status_code == 200
    course_titles = [c["title"] for c in response.json()]
    assert test_course.title in course_titles
    assert test_draft_course.title in course_titles
    assert test_archived_course.title in course_titles


@pytest.mark.asyncio
async def test_get_courses_as_teacher(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_course: Course,
    test_draft_course: Course,
    test_archived_course: Course,
    override_get_current_user_teacher,
):
    unique_username = f"other_teacher_{uuid.uuid4().hex}"
    other_teacher_user_obj = User(
        username=unique_username,
        email=f"{unique_username}@example.com",
        role=UserRole.teacher,
        hashed_password="hashed",
        is_active=True,
    )
    test_db.add(other_teacher_user_obj)
    await test_db.flush()
    await test_db.refresh(other_teacher_user_obj)

    other_published_course = Course(
        title="Other Published Course",
        description="Owned by another teacher, published",
        status=ObjectStatus.published,
        owner_id=other_teacher_user_obj.id,
        price=1000,
    )
    test_db.add(other_published_course)
    await test_db.flush()
    await test_db.refresh(other_published_course)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/")
    assert response.status_code == 200
    course_titles = [c["title"] for c in response.json()]
    assert test_course.title in course_titles
    assert test_draft_course.title in course_titles
    assert test_archived_course.title in course_titles
    assert other_published_course.title in course_titles


@pytest.mark.asyncio
async def test_get_courses_as_student(
    test_db: AsyncSession,
    test_user: User,
    test_course: Course,
    test_draft_course: Course,
    test_archived_course: Course,
    override_get_current_user_student,
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/")
    assert response.status_code == 200
    course_titles = [c["title"] for c in response.json()]
    assert test_course.title in course_titles
    assert test_draft_course.title not in course_titles
    assert test_archived_course.title not in course_titles


@pytest.mark.asyncio
async def test_get_my_courses_as_teacher(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_course: Course,
    test_draft_course: Course,
    test_archived_course: Course,
    override_get_current_user_teacher,
):
    unique_username = f"other_teacher_for_my_{uuid.uuid4().hex}"
    other_teacher_user_obj = User(
        username=unique_username,
        email=f"{unique_username}@example.com",
        role=UserRole.teacher,
        hashed_password="hashed",
        is_active=True,
    )
    test_db.add(other_teacher_user_obj)
    await test_db.flush()
    await test_db.refresh(other_teacher_user_obj)

    other_course = Course(
        title="Other Teacher's Course",
        description="Should not appear in my courses",
        status=ObjectStatus.published,
        owner_id=other_teacher_user_obj.id,
        price=100,
    )
    test_db.add(other_course)
    await test_db.flush()
    await test_db.refresh(other_course)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/my")
    assert response.status_code == 200
    course_titles = [c["title"] for c in response.json()]
    assert test_course.title in course_titles
    assert test_draft_course.title in course_titles
    assert test_archived_course.title not in course_titles
    assert other_course.title not in course_titles


@pytest.mark.asyncio
async def test_get_my_courses_as_student_forbidden(
    test_db: AsyncSession, test_user: User, override_get_current_user_student
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/my")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_archived_content_tree_as_teacher(
    test_db: AsyncSession,
    test_teacher_user: User,
    test_archived_course: Course,
    test_course: Course,
    override_get_current_user_teacher,
):
    archived_module_in_published_course = Module(
        title="Archived Mod in Pub Course",
        description="Archived Module Description",
        course_id=test_course.id,
        status=ObjectStatus.archived,
        order=1,
    )

    test_db.add(archived_module_in_published_course)

    await test_db.flush()
    await test_db.refresh(archived_module_in_published_course)

    archived_lesson_in_published_course = Lesson(
        title="Archived Lesson in Pub Course",
        summary="Archived Lesson Description",
        module_id=archived_module_in_published_course.id,
        course_id=test_course.id,
        status=ObjectStatus.archived,
        order=1,
    )
    test_db.add(archived_lesson_in_published_course)
    await test_db.flush()
    await test_db.refresh(archived_module_in_published_course)
    await test_db.refresh(archived_lesson_in_published_course)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/archived/")
    assert response.status_code == 200
    archived_data = response.json()

    found_archived_course = next(
        (c for c in archived_data if c["id"] == test_archived_course.id), None
    )
    assert found_archived_course is not None
    assert found_archived_course["title"] == test_archived_course.title
    assert found_archived_course["status"] == ObjectStatus.archived.value

    found_course_with_archived_content = next(
        (c for c in archived_data if c["id"] == test_course.id), None
    )
    assert found_course_with_archived_content is not None
    assert found_course_with_archived_content["title"] == test_course.title
    assert (
        found_course_with_archived_content["status"]
        == ObjectStatus.published.value
    )

    archived_module_titles = [
        m["title"] for c in archived_data for m in c.get("modules", [])
    ]
    archived_lesson_titles = [
        l["title"]
        for c in archived_data
        for m in c.get("modules", [])
        for l in m.get("lessons", [])
    ]
    assert archived_module_in_published_course.title in archived_module_titles
    assert archived_lesson_in_published_course.title in archived_lesson_titles


@pytest.mark.asyncio
async def test_get_archived_content_tree_as_student_forbidden(
    test_db: AsyncSession, test_user: User, override_get_current_user_student
):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/course/archived/")
    assert response.status_code == 403
