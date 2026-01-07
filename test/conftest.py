"""
Pytest configuration and fixtures for CMS project tests
"""

import os
import sys
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta

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


# Mock Redis Session Manager for testing
class MockRedisSessionManager:
    """
    Mock Redis session manager for testing without actual Redis connection.
    Stores sessions in memory using a dictionary.
    """

    def __init__(self):
        self._sessions = {}  # session_id -> session_data
        self._user_sessions = {}  # user_id -> set of session_ids
        self._redis = None  # Mock redis connection (not used but checked)
        self._pool = None  # Mock connection pool

    def connect_sync(self):
        """Mock connect - does nothing (sync version)"""
        self._redis = True  # Set to truthy value to indicate connected

    async def connect(self):
        """Mock connect - async version for compatibility"""
        self.connect_sync()

    def disconnect_sync(self):
        """Mock disconnect - clears all sessions (sync version)"""
        self._sessions.clear()
        self._user_sessions.clear()

    async def disconnect(self):
        """Mock disconnect - async version for compatibility"""
        self.disconnect_sync()

    async def create_session(self, user_id: int, user_email: str, user_role: str, expires_in: int = 3600) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
        }

        self._sessions[session_id] = session_data

        # Track user sessions
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = set()
        self._user_sessions[user_id].add(session_id)

        return session_id

    async def get_session(self, session_id: str) -> dict | None:
        """Get session data by session ID"""
        session_data = self._sessions.get(session_id)
        if not session_data:
            return None

        # Check if expired
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if datetime.utcnow() > expires_at:
            await self.delete_session(session_id)
            return None

        return session_data

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by session ID"""
        if session_id in self._sessions:
            session_data = self._sessions[session_id]
            user_id = session_data["user_id"]

            # Remove from user sessions
            if user_id in self._user_sessions:
                self._user_sessions[user_id].discard(session_id)
                if not self._user_sessions[user_id]:
                    del self._user_sessions[user_id]

            del self._sessions[session_id]
            return True
        return False

    async def delete_all_user_sessions(self, user_id: int) -> int:
        """Delete all sessions for a user"""
        if user_id not in self._user_sessions:
            return 0

        session_ids = list(self._user_sessions[user_id])
        count = 0
        for session_id in session_ids:
            if await self.delete_session(session_id):
                count += 1

        return count

    async def get_active_sessions(self, user_id: int) -> list[dict]:
        """Get all active sessions for a user"""
        if user_id not in self._user_sessions:
            return []

        sessions = []
        for session_id in list(self._user_sessions[user_id]):
            session_data = await self.get_session(session_id)
            if session_data:
                sessions.append({"session_id": session_id, **session_data})

        return sessions


@pytest.fixture(scope="function")
def mock_session_manager():
    """Provide a mock Redis session manager for tests"""
    manager = MockRedisSessionManager()
    manager.connect_sync()
    yield manager
    manager.disconnect_sync()


@pytest.fixture(autouse=True)
def mock_redis_session(monkeypatch, mock_session_manager):
    """
    Auto-mock Redis session manager for all tests.
    This prevents tests from trying to connect to actual Redis.
    """
    from app.utils import session as session_module

    # Replace the global session_manager instance
    monkeypatch.setattr(session_module, "session_manager", mock_session_manager)

    # Mock get_session_manager to return our mock
    async def mock_get_session_manager():
        return mock_session_manager

    monkeypatch.setattr(session_module, "get_session_manager", mock_get_session_manager)

    return mock_session_manager
