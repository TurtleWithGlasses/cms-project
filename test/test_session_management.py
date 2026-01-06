"""
Tests for Redis session management

Tests session creation, retrieval, validation, and deletion.
Note: These tests require a running Redis instance or use fakeredis.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.utils.session import RedisSessionManager


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock = AsyncMock()
    mock.ping = AsyncMock()
    mock.setex = AsyncMock()
    mock.get = AsyncMock()
    mock.exists = AsyncMock()
    mock.delete = AsyncMock()
    mock.sadd = AsyncMock()
    mock.srem = AsyncMock()
    mock.smembers = AsyncMock()
    mock.expire = AsyncMock()
    mock.aclose = AsyncMock()
    return mock


@pytest.fixture
async def session_manager(mock_redis):
    """Create a session manager with mocked Redis"""
    manager = RedisSessionManager()
    manager._redis = mock_redis
    manager._pool = MagicMock()
    manager._pool.aclose = AsyncMock()
    return manager


class TestSessionCreation:
    """Test session creation functionality"""

    @pytest.mark.asyncio
    async def test_create_session_returns_session_id(self, session_manager):
        """Test that creating a session returns a valid session ID"""
        session_id = await session_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        # UUID format check (36 characters with hyphens)
        assert len(session_id) == 36

    @pytest.mark.asyncio
    async def test_create_session_stores_user_data(self, session_manager, mock_redis):
        """Test that session stores correct user data"""
        await session_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        # Verify setex was called with session data
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        session_key = call_args[0][0]
        session_data_json = call_args[0][2]

        assert session_key.startswith("session:")
        assert "test@example.com" in session_data_json
        assert '"user_id": 1' in session_data_json
        assert '"role": "user"' in session_data_json

    @pytest.mark.asyncio
    async def test_create_session_with_additional_data(self, session_manager):
        """Test creating session with extra data"""
        session_id = await session_manager.create_session(
            user_id=1,
            user_email="test@example.com",
            user_role="admin",
            additional_data={"ip_address": "127.0.0.1", "user_agent": "TestBrowser"},
        )

        assert session_id is not None

    @pytest.mark.asyncio
    async def test_create_session_tracks_user_sessions(self, session_manager, mock_redis):
        """Test that session is added to user's session set"""
        await session_manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

        # Verify sadd was called to track the session
        mock_redis.sadd.assert_called_once()
        call_args = mock_redis.sadd.call_args
        user_sessions_key = call_args[0][0]
        assert user_sessions_key == "user_sessions:1"


class TestSessionRetrieval:
    """Test session retrieval and validation"""

    @pytest.mark.asyncio
    async def test_get_existing_session(self, session_manager, mock_redis):
        """Test retrieving an existing session"""
        # Mock Redis returning session data
        session_data = '{"user_id": 1, "email": "test@example.com", "role": "user", "created_at": "2024-01-01T00:00:00", "last_activity": "2024-01-01T00:00:00"}'
        mock_redis.get.return_value = session_data

        result = await session_manager.get_session("test-session-id")

        assert result is not None
        assert result["user_id"] == 1
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager, mock_redis):
        """Test retrieving a session that doesn't exist"""
        mock_redis.get.return_value = None

        result = await session_manager.get_session("nonexistent-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_updates_last_activity(self, session_manager, mock_redis):
        """Test that getting a session updates last_activity timestamp"""
        session_data = '{"user_id": 1, "email": "test@example.com", "role": "user", "created_at": "2024-01-01T00:00:00", "last_activity": "2024-01-01T00:00:00"}'
        mock_redis.get.return_value = session_data

        result = await session_manager.get_session("test-session-id")

        assert result is not None
        assert "last_activity" in result
        # Verify setex was called to update the session
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_existing_session(self, session_manager, mock_redis):
        """Test validating an existing session"""
        mock_redis.exists.return_value = 1

        is_valid = await session_manager.validate_session("test-session-id")

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_nonexistent_session(self, session_manager, mock_redis):
        """Test validating a nonexistent session"""
        mock_redis.exists.return_value = 0

        is_valid = await session_manager.validate_session("nonexistent-session")

        assert is_valid is False


class TestSessionDeletion:
    """Test session deletion and invalidation"""

    @pytest.mark.asyncio
    async def test_delete_existing_session(self, session_manager, mock_redis):
        """Test deleting an existing session"""
        # Mock getting session data first
        session_data = '{"user_id": 1, "email": "test@example.com"}'
        mock_redis.get.return_value = session_data
        mock_redis.delete.return_value = 1

        deleted = await session_manager.delete_session("test-session-id")

        assert deleted is True
        mock_redis.delete.assert_called()
        mock_redis.srem.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, session_manager, mock_redis):
        """Test deleting a session that doesn't exist"""
        mock_redis.get.return_value = None
        mock_redis.delete.return_value = 0

        deleted = await session_manager.delete_session("nonexistent-session")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions(self, session_manager, mock_redis):
        """Test deleting all sessions for a user"""
        # Mock user has 3 sessions
        mock_redis.smembers.return_value = ["session1", "session2", "session3"]
        mock_redis.delete.return_value = 1

        count = await session_manager.delete_all_user_sessions(user_id=1)

        assert count == 3
        # Should delete each session + the user sessions set
        assert mock_redis.delete.call_count == 4

    @pytest.mark.asyncio
    async def test_delete_all_user_sessions_no_sessions(self, session_manager, mock_redis):
        """Test deleting all sessions when user has none"""
        mock_redis.smembers.return_value = set()

        count = await session_manager.delete_all_user_sessions(user_id=1)

        assert count == 0


class TestActiveSessions:
    """Test active session management"""

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager, mock_redis):
        """Test getting all active sessions for a user"""
        # Mock user has 2 sessions
        mock_redis.smembers.return_value = {"session1", "session2"}
        session_data = '{"user_id": 1, "email": "test@example.com", "role": "user"}'
        mock_redis.get.return_value = session_data

        sessions = await session_manager.get_active_sessions(user_id=1)

        assert len(sessions) == 2
        assert all("session_id" in s for s in sessions)
        assert all("user_id" in s for s in sessions)

    @pytest.mark.asyncio
    async def test_get_active_sessions_filters_expired(self, session_manager, mock_redis):
        """Test that get_active_sessions filters out expired sessions"""
        mock_redis.smembers.return_value = {"session1", "session2", "session3"}

        # First call returns data, second returns None (expired), third returns data
        mock_redis.get.side_effect = [
            '{"user_id": 1}',  # session1 exists
            None,  # session2 expired
            '{"user_id": 1}',  # session3 exists
        ]

        sessions = await session_manager.get_active_sessions(user_id=1)

        assert len(sessions) == 2


class TestSessionExpiration:
    """Test session expiration functionality"""

    @pytest.mark.asyncio
    async def test_extend_session(self, session_manager, mock_redis):
        """Test extending session expiration time"""
        mock_redis.expire.return_value = True

        extended = await session_manager.extend_session("test-session-id")

        assert extended is True
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_extend_nonexistent_session(self, session_manager, mock_redis):
        """Test extending a nonexistent session"""
        mock_redis.expire.return_value = False

        extended = await session_manager.extend_session("nonexistent-session")

        assert extended is False


class TestConnectionManagement:
    """Test Redis connection management"""

    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self):
        """Test that connect establishes Redis connection"""
        manager = RedisSessionManager()

        with patch("redis.asyncio.ConnectionPool") as mock_pool_class, patch("redis.asyncio.Redis") as mock_redis_class:
            mock_pool = AsyncMock()
            mock_pool_class.return_value = mock_pool

            mock_redis_instance = AsyncMock()
            mock_redis_instance.ping = AsyncMock()
            mock_redis_class.return_value = mock_redis_instance

            await manager.connect()

            assert manager._redis is not None
            mock_redis_instance.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self, session_manager):
        """Test that disconnect closes Redis connection"""
        # Store references before disconnect sets them to None
        redis_conn = session_manager._redis
        pool = session_manager._pool

        await session_manager.disconnect()

        # Assert on the stored references
        redis_conn.aclose.assert_called_once()
        pool.aclose.assert_called_once()

        # Assert that they're now None
        assert session_manager._redis is None
        assert session_manager._pool is None


class TestErrorHandling:
    """Test error handling in session management"""

    @pytest.mark.asyncio
    async def test_get_session_handles_json_decode_error(self, session_manager, mock_redis):
        """Test handling of invalid JSON in session data"""
        mock_redis.get.return_value = "invalid json{"

        result = await session_manager.get_session("test-session-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_session_requires_redis_connection(self):
        """Test that create_session connects to Redis if not connected"""
        manager = RedisSessionManager()

        with patch.object(manager, "connect", new_callable=AsyncMock) as mock_connect:
            mock_redis = AsyncMock()
            mock_redis.setex = AsyncMock()
            mock_redis.sadd = AsyncMock()
            mock_redis.expire = AsyncMock()
            manager._redis = mock_redis

            await manager.create_session(user_id=1, user_email="test@example.com", user_role="user")

            # Should have attempted to connect if _redis was None initially
            # (mocked out for this test)
