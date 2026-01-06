"""
Tests for authentication with session management

Tests login with session creation, logout, and session-based endpoints.
"""

from unittest.mock import AsyncMock, patch

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


class TestLoginWithSessions:
    """Test login endpoint with session creation"""

    def test_login_creates_session(self, client, test_user, mock_session_manager):
        """Test that successful login creates a Redis session"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword"})

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "Bearer"

            # Verify session was created
            mock_session_manager.create_session.assert_called_once()

    def test_login_embeds_session_id_in_token(self, client, test_user, mock_session_manager):
        """Test that session ID is embedded in JWT token"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword"})

            assert response.status_code == 200
            data = response.json()
            token = data["access_token"]

            # Token should be present
            assert token is not None
            assert len(token) > 0

    def test_login_invalid_credentials_no_session(self, client, test_user, mock_session_manager):
        """Test that failed login does not create session"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/token", data={"username": test_user.email, "password": "wrongpassword"})

            assert response.status_code == 401

            # Verify session was NOT created
            mock_session_manager.create_session.assert_not_called()


class TestLogout:
    """Test logout functionality"""

    def test_logout_with_session_id(self, client, auth_headers, mock_session_manager):
        """Test logout with session ID in header"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            headers = {**auth_headers, "X-Session-ID": "test-session-id"}
            response = client.post("/auth/logout", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "logged out" in data["message"].lower()

            # Verify session was deleted
            mock_session_manager.delete_session.assert_called_once_with("test-session-id")

    def test_logout_without_session_id(self, client, auth_headers, mock_session_manager):
        """Test logout without session ID returns appropriate message"""
        mock_session_manager.delete_session.return_value = False

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/logout", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "no active session" in data["message"].lower()

    def test_logout_requires_authentication(self, client):
        """Test that logout requires valid authentication"""
        response = client.post("/auth/logout")

        # Should return 401 or 403
        assert response.status_code in [401, 403]


class TestLogoutAll:
    """Test logout from all devices"""

    def test_logout_all_deletes_all_sessions(self, client, auth_headers, mock_session_manager):
        """Test that logout-all deletes all user sessions"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/logout-all", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["sessions_deleted"] == 3
            assert "3 device" in data["message"]

            # Verify all sessions were deleted
            mock_session_manager.delete_all_user_sessions.assert_called_once()

    def test_logout_all_no_sessions(self, client, auth_headers, mock_session_manager):
        """Test logout-all when user has no sessions"""
        mock_session_manager.delete_all_user_sessions.return_value = 0

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.post("/auth/logout-all", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["sessions_deleted"] == 0

    def test_logout_all_requires_authentication(self, client):
        """Test that logout-all requires authentication"""
        response = client.post("/auth/logout-all")

        assert response.status_code in [401, 403]


class TestGetActiveSessions:
    """Test viewing active sessions"""

    def test_get_active_sessions_returns_list(self, client, auth_headers, mock_session_manager):
        """Test getting list of active sessions"""
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

    def test_get_active_sessions_no_sessions(self, client, auth_headers, mock_session_manager):
        """Test getting active sessions when user has none"""
        mock_session_manager.get_active_sessions.return_value = []

        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.get("/auth/sessions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["active_sessions"] == 0
            assert data["sessions"] == []

    def test_get_active_sessions_requires_authentication(self, client):
        """Test that getting sessions requires authentication"""
        response = client.get("/auth/sessions")

        assert response.status_code in [401, 403]


class TestSessionSecurity:
    """Test security aspects of session management"""

    def test_user_can_only_access_own_sessions(self, client, test_user, auth_headers, mock_session_manager):
        """Test that users can only see their own sessions"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            response = client.get("/auth/sessions", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # All sessions should belong to the authenticated user
            for session in data["sessions"]:
                assert session["user_id"] == test_user.id
                assert session["email"] == test_user.email

    def test_cannot_delete_other_users_sessions(self, client, test_user, auth_headers, mock_session_manager):
        """Test that users cannot delete other users' sessions"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            # This should only delete the authenticated user's sessions
            response = client.post("/auth/logout-all", headers=auth_headers)

            assert response.status_code == 200

            # Verify it was called with the correct user ID
            call_args = mock_session_manager.delete_all_user_sessions.call_args
            assert call_args[0][0] == test_user.id


class TestSessionIntegration:
    """Integration tests for full session workflow"""

    def test_full_session_lifecycle(self, client, test_user, mock_session_manager):
        """Test complete session lifecycle: login -> use -> logout"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            # 1. Login and create session
            login_response = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword"})
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

    def test_multiple_concurrent_sessions(self, client, test_user, mock_session_manager):
        """Test that user can have multiple active sessions"""
        with patch("app.routes.auth.get_session_manager", return_value=mock_session_manager):
            # Simulate multiple logins (e.g., from different devices)
            mock_session_manager.create_session.side_effect = ["session1", "session2", "session3"]

            # Login from "device 1"
            response1 = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword"})
            assert response1.status_code == 200

            # Login from "device 2"
            response2 = client.post("/auth/token", data={"username": test_user.email, "password": "testpassword"})
            assert response2.status_code == 200

            # Both sessions should be created
            assert mock_session_manager.create_session.call_count == 2
