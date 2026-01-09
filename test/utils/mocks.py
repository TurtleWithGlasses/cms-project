"""
Mock utilities for testing complex dependencies

Provides mock implementations for:
- Activity logging
- Session management
- Database operations
"""

import contextlib
from typing import Any
from unittest.mock import MagicMock


class MockActivityLogger:
    """Mock for activity logging that tracks calls without database operations"""

    def __init__(self):
        self.logs = []
        self.call_count = 0

    async def log_activity(
        self, action: str, user_id: int | None = None, content_id: int | None = None, description: str = "", **kwargs
    ):
        """Mock log_activity that stores calls in memory"""
        self.call_count += 1
        log_entry = {
            "action": action,
            "user_id": user_id,
            "content_id": content_id,
            "description": description,
            **kwargs,
        }
        self.logs.append(log_entry)
        return log_entry

    def get_logs_for_user(self, user_id: int):
        """Get all logs for a specific user"""
        return [log for log in self.logs if log.get("user_id") == user_id]

    def get_logs_for_action(self, action: str):
        """Get all logs for a specific action"""
        return [log for log in self.logs if log.get("action") == action]

    def clear(self):
        """Clear all logged entries"""
        self.logs.clear()
        self.call_count = 0


class MockSessionManager:
    """Mock for Redis session management"""

    def __init__(self):
        self.sessions = {}
        self.session_counter = 0

    async def create_session(self, user_id: int, user_email: str, user_role: str) -> str:
        """Create a mock session and return session ID"""
        self.session_counter += 1
        session_id = f"mock_session_{self.session_counter}"
        self.sessions[session_id] = {"user_id": user_id, "user_email": user_email, "user_role": user_role}
        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data by ID"""
        return self.sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    async def delete_all_user_sessions(self, user_id: int) -> int:
        """Delete all sessions for a user"""
        sessions_to_delete = [sid for sid, data in self.sessions.items() if data.get("user_id") == user_id]
        for sid in sessions_to_delete:
            del self.sessions[sid]
        return len(sessions_to_delete)

    async def get_active_sessions(self, user_id: int) -> list[dict]:
        """Get all active sessions for a user"""
        return [{"session_id": sid, **data} for sid, data in self.sessions.items() if data.get("user_id") == user_id]

    def clear(self):
        """Clear all sessions"""
        self.sessions.clear()
        self.session_counter = 0


class MockDatabaseError:
    """Mock for simulating database errors"""

    def __init__(self, should_fail: bool = False, error_message: str = "Mock database error"):
        self.should_fail = should_fail
        self.error_message = error_message
        self.call_count = 0

    async def execute(self, *args, **kwargs):
        """Mock database execute that can be configured to fail"""
        self.call_count += 1
        if self.should_fail:
            raise Exception(self.error_message)
        return MagicMock()

    async def commit(self):
        """Mock commit that can be configured to fail"""
        if self.should_fail:
            raise Exception(self.error_message)

    async def rollback(self):
        """Mock rollback"""
        pass


def create_mock_activity_logger():
    """Factory function to create a new mock activity logger"""
    return MockActivityLogger()


def create_mock_session_manager():
    """Factory function to create a new mock session manager"""
    return MockSessionManager()


def patch_activity_logging(monkeypatch, mock_logger: MockActivityLogger | None = None):
    """
    Patch activity logging in application code

    Usage:
        mock_logger = create_mock_activity_logger()
        patch_activity_logging(monkeypatch, mock_logger)
    """
    if mock_logger is None:
        mock_logger = create_mock_activity_logger()

    # Patch in routes
    monkeypatch.setattr("app.routes.content.log_activity", mock_logger.log_activity)
    monkeypatch.setattr("app.routes.user.log_activity", mock_logger.log_activity)

    # Patch in services if needed
    with contextlib.suppress(AttributeError):
        monkeypatch.setattr("app.services.password_reset_service.log_activity", mock_logger.log_activity)

    return mock_logger


def patch_session_manager(monkeypatch, mock_manager: MockSessionManager | None = None):
    """
    Patch session manager in application code

    Usage:
        mock_manager = create_mock_session_manager()
        patch_session_manager(monkeypatch, mock_manager)
    """
    if mock_manager is None:
        mock_manager = create_mock_session_manager()

    async def mock_get_session_manager():
        return mock_manager

    monkeypatch.setattr("app.routes.auth.get_session_manager", mock_get_session_manager)
    monkeypatch.setattr("app.auth.get_session_manager", mock_get_session_manager)

    return mock_manager
