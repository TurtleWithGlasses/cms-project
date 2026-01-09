"""
Reusable pytest fixtures for integration testing

Provides fixtures for:
- Mock activity logging
- Mock session management
- Database error simulation
"""

import contextlib

import pytest

from .mocks import create_mock_activity_logger, create_mock_session_manager


@pytest.fixture
def mock_activity_logger():
    """Fixture providing a mock activity logger"""
    logger = create_mock_activity_logger()
    yield logger
    logger.clear()


@pytest.fixture
def mock_session_manager():
    """Fixture providing a mock session manager"""
    manager = create_mock_session_manager()
    yield manager
    manager.clear()


@pytest.fixture
def patch_activity_logging_fixture(monkeypatch, mock_activity_logger):
    """Fixture that patches activity logging across the application"""
    # Patch in routes
    monkeypatch.setattr("app.routes.content.log_activity", mock_activity_logger.log_activity)
    monkeypatch.setattr("app.routes.user.log_activity", mock_activity_logger.log_activity)

    # Patch in services
    with contextlib.suppress(AttributeError):
        monkeypatch.setattr("app.services.password_reset_service.log_activity", mock_activity_logger.log_activity)

    return mock_activity_logger


@pytest.fixture
def patch_session_manager_fixture(monkeypatch, mock_session_manager):
    """Fixture that patches session manager across the application"""

    async def mock_get_session_manager():
        return mock_session_manager

    monkeypatch.setattr("app.routes.auth.get_session_manager", mock_get_session_manager)
    with contextlib.suppress(AttributeError):
        monkeypatch.setattr("app.auth.get_session_manager", mock_get_session_manager)

    return mock_session_manager


@pytest.fixture
def fully_mocked_dependencies(patch_activity_logging_fixture, patch_session_manager_fixture):
    """
    Fixture that patches all complex dependencies

    Returns a dict with:
    - activity_logger: MockActivityLogger instance
    - session_manager: MockSessionManager instance
    """
    return {
        "activity_logger": patch_activity_logging_fixture,
        "session_manager": patch_session_manager_fixture,
    }
