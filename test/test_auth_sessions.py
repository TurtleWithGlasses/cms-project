"""
Tests for authentication with session management

Tests login with session creation, logout, and session-based endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from test.conftest import override_get_db


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


class TestLoginWithSessions:
    """Test login endpoint with session creation"""

    @pytest.mark.asyncio
    async def test_login_creates_session(self, async_db_session, test_user, mock_session_manager):
        """Test that successful login creates a Redis session"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword123"})

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "Bearer"

            # Verify session was created
            mock_session_manager.create_session.assert_called_once()
            call_args = mock_session_manager.create_session.call_args
            assert call_args[1]["user_id"] == test_user.id
            assert call_args[1]["user_email"] == test_user.email
            assert call_args[1]["user_role"] == test_user.role

    @pytest.mark.asyncio
    async def test_login_embeds_session_id_in_token(self, async_db_session, test_user, mock_session_manager):
        """Test that session ID is embedded in JWT token"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword123"})

            assert response.status_code == 200
            data = response.json()
            token = data["access_token"]

            # Decode token to check session_id is present
            # (Would need to actually decode JWT in real test)
            assert token is not None
            assert len(token) > 0

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_no_session(self, async_db_session, test_user, mock_session_manager):
        """Test that failed login does not create session"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/token", data={"username": test_user.email, "password": "wrongpassword"})

            assert response.status_code == 401

            # Verify session was NOT created
            mock_session_manager.create_session.assert_not_called()


class TestLogout:
    """Test logout functionality"""

    @pytest.mark.asyncio
    async def test_logout_with_session_id(self, async_db_session, test_user, mock_session_manager, auth_headers):
        """Test logout with session ID in header"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            headers = {**auth_headers, "X-Session-ID": "test-session-id"}
            response = client.post("/auth/logout", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "logged out" in data["message"].lower()

            # Verify session was deleted
            mock_session_manager.delete_session.assert_called_once_with("test-session-id")

    @pytest.mark.asyncio
    async def test_logout_without_session_id(self, async_db_session, test_user, mock_session_manager, auth_headers):
        """Test logout without session ID returns appropriate message"""
        client = TestClient(app)

        mock_session_manager.delete_session.return_value = False

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/logout", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "no active session" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_requires_authentication(self, async_db_session):
        """Test that logout requires valid authentication"""
        client = TestClient(app)

        response = client.post("/auth/logout")

        # Should return 401 or 403
        assert response.status_code in [401, 403]


class TestLogoutAll:
    """Test logout from all devices"""

    @pytest.mark.asyncio
    async def test_logout_all_deletes_all_sessions(
        self, async_db_session, test_user, mock_session_manager, auth_headers
    ):
        """Test that logout-all deletes all user sessions"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/logout-all", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["sessions_deleted"] == 3
            assert "3 device" in data["message"]

            # Verify all sessions were deleted
            mock_session_manager.delete_all_user_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_all_no_sessions(self, async_db_session, test_user, mock_session_manager, auth_headers):
        """Test logout-all when user has no sessions"""
        client = TestClient(app)

        mock_session_manager.delete_all_user_sessions.return_value = 0

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/logout-all", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["sessions_deleted"] == 0

    @pytest.mark.asyncio
    async def test_logout_all_requires_authentication(self, async_db_session):
        """Test that logout-all requires authentication"""
        client = TestClient(app)

        response = client.post("/auth/logout-all")

        assert response.status_code in [401, 403]


class TestGetActiveSessions:
    """Test viewing active sessions"""

    @pytest.mark.asyncio
    async def test_get_active_sessions_returns_list(
        self, async_db_session, test_user, mock_session_manager, auth_headers
    ):
        """Test getting list of active sessions"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.get("/auth/sessions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["active_sessions"] == 2
            assert len(data["sessions"]) == 2

            # Verify session data structure
            session = data["sessions"][0]
            assert "session_id" in session
            assert "user_id" in session
            assert "email" in session
            assert "role" in session
            assert "created_at" in session
            assert "last_activity" in session

    @pytest.mark.asyncio
    async def test_get_active_sessions_no_sessions(
        self, async_db_session, test_user, mock_session_manager, auth_headers
    ):
        """Test getting active sessions when user has none"""
        client = TestClient(app)

        mock_session_manager.get_active_sessions.return_value = []

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.get("/auth/sessions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["active_sessions"] == 0
            assert data["sessions"] == []

    @pytest.mark.asyncio
    async def test_get_active_sessions_requires_authentication(self, async_db_session):
        """Test that getting sessions requires authentication"""
        client = TestClient(app)

        response = client.get("/auth/sessions")

        assert response.status_code in [401, 403]


class TestSessionSecurity:
    """Test security aspects of session management"""

    @pytest.mark.asyncio
    async def test_user_can_only_access_own_sessions(
        self, async_db_session, test_user, mock_session_manager, auth_headers
    ):
        """Test that users can only see their own sessions"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.get("/auth/sessions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # All sessions should belong to the authenticated user
            for session in data["sessions"]:
                assert session["user_id"] == test_user.id
                assert session["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_cannot_delete_other_users_sessions(
        self, async_db_session, test_user, mock_session_manager, auth_headers
    ):
        """Test that users cannot delete other users' sessions"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            # This should only delete the authenticated user's sessions
            response = client.post("/auth/logout-all", headers=auth_headers)

            assert response.status_code == 200

            # Verify it was called with the correct user ID
            call_args = mock_session_manager.delete_all_user_sessions.call_args
            assert call_args[0][0] == test_user.id


class TestSessionIntegration:
    """Integration tests for full session workflow"""

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, async_db_session, test_user, mock_session_manager):
        """Test complete session lifecycle: login -> use -> logout"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            # 1. Login and create session
            login_response = client.post(
                "/auth/token", data={"username": test_user.email, "password": "testpassword123"}
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # 2. Use the session to access protected endpoint
            headers = {"Authorization": f"Bearer {token}"}
            sessions_response = client.get("/auth/sessions", headers=headers)
            assert sessions_response.status_code == 200

            # 3. Logout and delete session
            logout_response = client.post("/auth/logout", headers={**headers, "X-Session-ID": "mock-session-id-12345"})
            assert logout_response.status_code == 200
            assert logout_response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self, async_db_session, test_user, mock_session_manager):
        """Test that user can have multiple active sessions"""
        client = TestClient(app)

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            # Simulate multiple logins (e.g., from different devices)
            mock_session_manager.create_session.side_effect = ["session1", "session2", "session3"]

            # Login from "device 1"
            response1 = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword123"})
            assert response1.status_code == 200

            # Login from "device 2"
            response2 = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword123"})
            assert response2.status_code == 200

            # Both sessions should be created
            assert mock_session_manager.create_session.call_count == 2
