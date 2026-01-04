"""
Pytest configuration and fixtures for CMS project tests
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models.user import User, Role
from app.auth import hash_password
from main import app


# Test database URL (SQLite in-memory for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test function.
    """
    # Create async engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        # Create default roles
        roles_data = [
            {"name": "user", "permissions": []},
            {"name": "editor", "permissions": ["view_content", "edit_content"]},
            {"name": "manager", "permissions": ["view_content", "edit_content", "approve_content"]},
            {"name": "admin", "permissions": ["*"]},
            {"name": "superadmin", "permissions": ["*"]},
        ]

        for role_data in roles_data:
            role = Role(**role_data)
            session.add(role)

        await session.commit()

        yield session

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def client(override_get_db):
    """Create a test client for the FastAPI application with test database"""
    # The override_get_db fixture will set up the database override
    return TestClient(app)


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create a test user with 'user' role"""
    from sqlalchemy.future import select

    # Get user role
    result = await test_db.execute(select(Role).where(Role.name == "user"))
    user_role = result.scalars().first()

    # Create user
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=hash_password("testpassword"),
        role_id=user_role.id
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    return user


@pytest.fixture
async def test_admin(test_db: AsyncSession) -> User:
    """Create a test admin user"""
    from sqlalchemy.future import select

    # Get admin role
    result = await test_db.execute(select(Role).where(Role.name == "admin"))
    admin_role = result.scalars().first()

    # Create admin
    admin = User(
        username="testadmin",
        email="admin@example.com",
        hashed_password=hash_password("adminpassword"),
        role_id=admin_role.id
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)

    return admin


@pytest.fixture
async def test_editor(test_db: AsyncSession) -> User:
    """Create a test editor user"""
    from sqlalchemy.future import select

    # Get editor role
    result = await test_db.execute(select(Role).where(Role.name == "editor"))
    editor_role = result.scalars().first()

    # Create editor
    editor = User(
        username="testeditor",
        email="editor@example.com",
        hashed_password=hash_password("editorpassword"),
        role_id=editor_role.id
    )
    test_db.add(editor)
    await test_db.commit()
    await test_db.refresh(editor)

    return editor


@pytest.fixture(scope="function", autouse=True)
def override_get_db(test_db: AsyncSession):
    """Override the get_db dependency for testing"""
    async def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()
