import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, ObjectStatus
from app.db.user import User, UserRole
from app.db.course import Course
from app.db.module import Module
from app.db.lesson import Lesson
from app.db.course_purchase import CoursePurchase

from app.app import app
from app.db import get_async_db_session
from app.dependencies import get_current_user, get_current_user_teacher

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(async_engine):
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def test_user(test_db: AsyncSession) -> User:
    user = User(
        username="testuser",
        email="testuser@example.com",
        role=UserRole.student,
        hashed_password="fakehashed",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_teacher_user(test_db: AsyncSession) -> User:
    user = User(
        username="teacher",
        email="teacher@example.com",
        role=UserRole.teacher,
        hashed_password="fakehashed",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin_user(test_db: AsyncSession) -> User:
    user = User(
        username="admin",
        email="admin@example.com",
        role=UserRole.admin,
        hashed_password="fakehashed",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_another_teacher_user(test_db: AsyncSession) -> User:
    user = User(
        username="another_teacher_user",
        email="another_teacher@example.com",
        role=UserRole.teacher,
        hashed_password="fakehashed",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_course(test_db: AsyncSession, test_teacher_user: User) -> Course:
    course = Course(
        title="Test Course",
        description="Test Description",
        status=ObjectStatus.published,
        owner_id=test_teacher_user.id,
        price=1000,
    )
    test_db.add(course)
    await test_db.flush()
    await test_db.refresh(course)
    return course


@pytest_asyncio.fixture
async def test_draft_course(
    test_db: AsyncSession, test_teacher_user: User
) -> Course:
    course = Course(
        title="Draft Course",
        description="This is a draft course",
        status=ObjectStatus.draft,
        owner_id=test_teacher_user.id,
        price=1000,
    )
    test_db.add(course)
    await test_db.flush()
    await test_db.refresh(course)
    return course


@pytest_asyncio.fixture
async def test_archived_course(
    test_db: AsyncSession, test_teacher_user: User
) -> Course:
    course = Course(
        title="Archived Course",
        description="This is an archived course",
        status=ObjectStatus.archived,
        owner_id=test_teacher_user.id,
        price=1000,
    )
    test_db.add(course)
    await test_db.flush()
    await test_db.refresh(course)
    return course


@pytest_asyncio.fixture
async def test_module(test_db: AsyncSession, test_course: Course) -> Module:
    module = Module(
        title="Test Module",
        description="Module Description",
        course_id=test_course.id,
        status=ObjectStatus.published,
        order=1,
    )
    test_db.add(module)
    await test_db.flush()
    await test_db.refresh(module)
    return module


@pytest_asyncio.fixture
async def test_draft_module(
    test_db: AsyncSession, test_course: Course
) -> Module:
    module = Module(
        title="Draft Module",
        description="Draft Module Description",
        course_id=test_course.id,
        status=ObjectStatus.draft,
        order=2,
    )
    test_db.add(module)
    await test_db.flush()
    await test_db.refresh(module)
    return module


@pytest_asyncio.fixture
async def test_archived_module(
    test_db: AsyncSession, test_course: Course
) -> Module:
    module = Module(
        title="Archived Module",
        description="Archived Module Description",
        course_id=test_course.id,
        status=ObjectStatus.archived,
        order=3,
    )
    test_db.add(module)
    await test_db.flush()
    await test_db.refresh(module)
    return module


@pytest_asyncio.fixture
async def test_lesson(test_db: AsyncSession, test_module: Module) -> Lesson:
    lesson = Lesson(
        title="Test Lesson",
        summary="Lesson Description",
        module_id=test_module.id,
        course_id=test_module.course_id,
        status=ObjectStatus.published,
        order=1,
    )
    test_db.add(lesson)
    await test_db.flush()
    await test_db.refresh(lesson)
    return lesson


@pytest_asyncio.fixture
async def test_course_lesson_without_module(
    test_db: AsyncSession, test_course: Course
) -> Lesson:
    lesson = Lesson(
        title="Course Lesson",
        summary="Lesson without module",
        course_id=test_course.id,
        status=ObjectStatus.published,
        order=1,
    )
    test_db.add(lesson)
    await test_db.flush()
    await test_db.refresh(lesson)
    return lesson


@pytest_asyncio.fixture
async def test_course_purchase(
    test_db: AsyncSession, test_user: User, test_course: Course
) -> CoursePurchase:
    purchase = CoursePurchase(
        user_id=test_user.id, course_id=test_course.id, transaction_id=1
    )
    test_db.add(purchase)
    await test_db.flush()
    await test_db.refresh(purchase)
    return purchase


@pytest.fixture(autouse=True)
def override_db_session(test_db: AsyncSession):
    app.dependency_overrides[get_async_db_session] = lambda: test_db
    yield
    app.dependency_overrides.pop(get_async_db_session, None)


@pytest.fixture
def override_get_current_user_student(test_user: User):
    async def _override_user():
        return test_user

    app.dependency_overrides[get_current_user] = _override_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def override_get_current_user_teacher(test_teacher_user: User):
    async def _override_teacher_user():
        return test_teacher_user

    app.dependency_overrides[get_current_user] = _override_teacher_user
    app.dependency_overrides[get_current_user_teacher] = _override_teacher_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_teacher, None)


@pytest.fixture
def override_get_current_user_admin(test_admin_user: User):
    async def _override_admin_user():
        return test_admin_user

    app.dependency_overrides[get_current_user] = _override_admin_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
