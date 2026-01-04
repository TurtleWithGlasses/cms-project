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
from fastapi.testclient import TestClient

# Import Base first, before importing the app
from app.database import Base
from app.models.user import User, Role
from app.auth import hash_password
from app.config import settings

# Test database URL - Use PostgreSQL for tests to match production
# Can be overridden with TEST_DATABASE_URL environment variable
# Default: appends '_test' to production database name
def get_test_database_url():
    """Get test database URL from environment or derive from production URL"""
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        return test_url

    # Derive from production URL by changing database name
    prod_url = settings.database_url
    # Change database name from 'cms_project' to 'cms_project_test' (or append _test to existing name)
    if prod_url:
        # Split URL to get database name and replace it
        parts = prod_url.rsplit('/', 1)
        if len(parts) == 2:
            base_url, db_name = parts
            test_db_name = f"{db_name}_test" if db_name else "cms_test"
            return f"{base_url}/{test_db_name}"

    # Fallback to a default test database
    return "postgresql+asyncpg://postgres:postgres@localhost/cms_test"

TEST_DATABASE_URL = get_test_database_url()

# Create test engine and session maker BEFORE importing the app
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using
)

TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

# Now import and patch the app's database components
import app.database as database_module
from main import app

# Replace the app's engine and session maker with test versions
database_module.engine = test_engine
database_module.AsyncSessionLocal = TestSessionLocal
database_module.async_session = TestSessionLocal


def setup_test_db_sync():
    """
    Synchronously set up the test database with tables and roles.
    This runs in the same event loop as TestClient.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _setup():
        # Create all tables
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create default roles
        async with TestSessionLocal() as session:
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

    loop.run_until_complete(_setup())
    loop.close()


def teardown_test_db_sync():
    """Synchronously drop all tables after test"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    loop.run_until_complete(_teardown())
    loop.close()


@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """
    Create a fresh database for each test function.
    Runs synchronously to work with TestClient.
    """
    setup_test_db_sync()
    yield
    teardown_test_db_sync()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for tests that need it.
    """
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def client():
    """Create a test client for the FastAPI application with test database"""
    # Database is already patched at module level
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


