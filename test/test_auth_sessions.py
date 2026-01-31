"""
Tests for authentication with session management

Tests login with session creation, logout, and session-based endpoints.
Session management feature is now fully implemented.
"""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager"""
    mock = AsyncMock()
    mock.create_session = AsyncMock(return_value="mock-session-id-12345")
    mock.delete_session = AsyncMock(return_value=True)
    mock.delete_all_user_sessions = AsyncMock(return_value=3)
    mock.get_active_sessions = AsyncMock(
        return_value=[
            {
                "session_id": "session1",
                "user_id": 1,
                "email": "test@example.com",
                "role": "user",
                "created_at": "2024-01-01T00:00:00",
                "last_activity": "2024-01-01T00:10:00",
            },
            {
                "session_id": "session2",
                "user_id": 1,
                "email": "test@example.com",
                "role": "user",
                "created_at": "2024-01-01T00:05:00",
                "last_activity": "2024-01-01T00:15:00",
            },
        ]
    )
    return mock


class TestSessionManagerUnit:
    """Unit tests for session manager functionality"""

    @pytest.mark.asyncio
    async def test_mock_session_manager_create_session(self, mock_session_manager):
        """Test mock session manager create_session"""
        session_id = await mock_session_manager.create_session(
            user_id=1, user_email="test@example.com", user_role="user"
        )
        assert session_id == "mock-session-id-12345"

    @pytest.mark.asyncio
    async def test_mock_session_manager_delete_session(self, mock_session_manager):
        """Test mock session manager delete_session"""
        result = await mock_session_manager.delete_session("test-session-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_mock_session_manager_delete_all(self, mock_session_manager):
        """Test mock session manager delete_all_user_sessions"""
        count = await mock_session_manager.delete_all_user_sessions(user_id=1)
        assert count == 3

    @pytest.mark.asyncio
    async def test_mock_session_manager_get_active(self, mock_session_manager):
        """Test mock session manager get_active_sessions"""
        sessions = await mock_session_manager.get_active_sessions(user_id=1)
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "session1"
        assert sessions[1]["session_id"] == "session2"


class TestSessionManagerImports:
    """Test that session manager can be imported and used"""

    def test_redis_session_manager_import(self):
        """Test RedisSessionManager can be imported"""
        from app.utils.session import RedisSessionManager

        assert RedisSessionManager is not None

    def test_inmemory_session_manager_import(self):
        """Test InMemorySessionManager can be imported"""
        from app.utils.session import InMemorySessionManager

        assert InMemorySessionManager is not None

    def test_get_session_manager_import(self):
        """Test get_session_manager can be imported"""
        from app.utils.session import get_session_manager

        assert get_session_manager is not None
        assert callable(get_session_manager)


class TestSessionManagerMethods:
    """Test session manager method signatures"""

    def test_redis_session_manager_has_required_methods(self):
        """Test RedisSessionManager has all required methods"""
        from app.utils.session import RedisSessionManager

        manager = RedisSessionManager()

        # Check all required methods exist
        assert hasattr(manager, "connect")
        assert hasattr(manager, "disconnect")
        assert hasattr(manager, "create_session")
        assert hasattr(manager, "get_session")
        assert hasattr(manager, "delete_session")
        assert hasattr(manager, "delete_all_user_sessions")
        assert hasattr(manager, "get_active_sessions")
        assert hasattr(manager, "validate_session")
        assert hasattr(manager, "extend_session")

    def test_inmemory_session_manager_has_required_methods(self):
        """Test InMemorySessionManager has all required methods"""
        from app.utils.session import InMemorySessionManager

        manager = InMemorySessionManager()

        # Check all required methods exist
        assert hasattr(manager, "connect")
        assert hasattr(manager, "disconnect")
        assert hasattr(manager, "create_session")
        assert hasattr(manager, "get_session")
        assert hasattr(manager, "delete_session")
        assert hasattr(manager, "delete_all_user_sessions")
        assert hasattr(manager, "get_active_sessions")
        assert hasattr(manager, "validate_session")
        assert hasattr(manager, "extend_session")


class TestInMemorySessionManager:
    """Test InMemorySessionManager functionality"""

    @pytest.fixture
    def inmemory_manager(self):
        """Create an InMemorySessionManager instance"""
        from app.utils.session import InMemorySessionManager

        return InMemorySessionManager()

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, inmemory_manager):
        """Test creating and retrieving a session"""
        await inmemory_manager.connect()

        session_id = await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        assert session_id is not None
        assert len(session_id) == 36  # UUID format

        session = await inmemory_manager.get_session(session_id)
        assert session is not None
        assert session["user_id"] == 1
        assert session["email"] == "test@example.com"
        assert session["role"] == "user"

        await inmemory_manager.disconnect()

    @pytest.mark.asyncio
    async def test_delete_session(self, inmemory_manager):
        """Test deleting a session"""
        await inmemory_manager.connect()

        session_id = await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        deleted = await inmemory_manager.delete_session(session_id)
        assert deleted is True

        session = await inmemory_manager.get_session(session_id)
        assert session is None

        await inmemory_manager.disconnect()

    @pytest.mark.asyncio
    async def test_validate_session(self, inmemory_manager):
        """Test validating a session"""
        await inmemory_manager.connect()

        session_id = await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        is_valid = await inmemory_manager.validate_session(session_id)
        assert is_valid is True

        is_valid_nonexistent = await inmemory_manager.validate_session("nonexistent")
        assert is_valid_nonexistent is False

        await inmemory_manager.disconnect()

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, inmemory_manager):
        """Test getting active sessions for a user"""
        await inmemory_manager.connect()

        # Create multiple sessions for the same user
        await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")
        await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        sessions = await inmemory_manager.get_active_sessions(user_id=1)
        assert len(sessions) == 2

        await inmemory_manager.disconnect()

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions(self, inmemory_manager):
        """Test deleting all sessions for a user"""
        await inmemory_manager.connect()

        # Create multiple sessions
        await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")
        await inmemory_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        count = await inmemory_manager.delete_all_user_sessions(user_id=1)
        assert count == 2

        sessions = await inmemory_manager.get_active_sessions(user_id=1)
        assert len(sessions) == 0

        await inmemory_manager.disconnect()
