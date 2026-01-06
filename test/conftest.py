"""
Pytest configuration and fixtures for CMS project tests
"""

import os
import sys
from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))  # noqa: PTH100, PTH118, PTH119, PTH120

# Import Base first, before importing the app
from app.auth import hash_password
from app.config import settings
from app.database import Base
from app.models.user import Role, User


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
        parts = prod_url.rsplit("/", 1)
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

TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Now import and patch the app's database components
import app.database as database_module  # noqa: E402
from main import app  # noqa: E402

# Replace the app's engine and session maker with test versions
database_module.engine = test_engine
database_module.AsyncSessionLocal = TestSessionLocal
database_module.async_session = TestSessionLocal


@pytest.fixture(scope="function")
async def setup_test_database():
    """
    Create a fresh database for each test function that needs it.
    Uses async/await properly with pytest-asyncio.
    Tests should depend on this fixture (or fixtures that depend on it like test_db)
    to trigger database setup.
    """
    # Drop all tables first to ensure clean state
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

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

    yield

    # Cleanup: drop all tables after test
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception as e:
        # Log but don't fail on cleanup errors
        import logging

        logging.warning(f"Error during test cleanup: {e}")


@pytest.fixture(scope="function")
async def test_db(setup_test_database) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for tests that need it.
    Depends on setup_test_database to ensure database is initialized.
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
        role_id=user_role.id,
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
        role_id=admin_role.id,
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
        role_id=editor_role.id,
    )
    test_db.add(editor)
    await test_db.commit()
    await test_db.refresh(editor)

    return editor


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Generate authentication headers for test user"""
    from datetime import timedelta

    from app.auth import create_access_token

    # Create a test token
    access_token = create_access_token(data={"sub": test_user.email}, expires_delta=timedelta(minutes=30))

    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(test_admin: User) -> dict:
    """Generate authentication headers for test admin"""
    from datetime import timedelta

    from app.auth import create_access_token

    access_token = create_access_token(data={"sub": test_admin.email}, expires_delta=timedelta(minutes=30))

    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def async_db_session(test_db: AsyncSession):
    """Alias for test_db for compatibility"""
    return test_db


def override_get_db():
    """Override database dependency for testing"""

    async def _override():
        async with TestSessionLocal() as session:
            yield session

    return _override
