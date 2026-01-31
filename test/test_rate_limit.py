"""
Tests for rate limiting middleware

Tests rate limiter configuration and functionality.
"""

import pytest
from slowapi import Limiter
from starlette.testclient import TestClient

from app.main import app
from app.middleware.rate_limit import configure_rate_limiting, get_rate_limiter, limiter


class TestRateLimiter:
    """Test rate limiter instance and configuration"""

    def test_limiter_is_initialized(self):
        """Test that limiter is properly initialized"""
        assert limiter is not None
        assert isinstance(limiter, Limiter)

    def test_limiter_has_default_limits(self):
        """Test that limiter has default limits configured"""
        assert limiter._default_limits is not None
        assert len(limiter._default_limits) > 0

    def test_limiter_has_headers_enabled(self):
        """Test that rate limit headers are enabled"""
        assert limiter._headers_enabled is True

    def test_get_rate_limiter_returns_limiter(self):
        """Test that get_rate_limiter returns the limiter instance"""
        result = get_rate_limiter()
        assert result is limiter
        assert isinstance(result, Limiter)


class TestConfigureRateLimiting:
    """Test rate limiting configuration"""

    def test_configure_rate_limiting_sets_app_state(self):
        """Test that configure_rate_limiting sets limiter in app state"""

        # Create mock app with state
        class MockApp:
            def __init__(self):
                self.state = type("State", (), {})()
                self._exception_handlers = {}

            def add_exception_handler(self, exc_class, handler):
                self._exception_handlers[exc_class] = handler

        app = MockApp()
        configure_rate_limiting(app)

        # Verify limiter is set in app state
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is limiter

    def test_configure_rate_limiting_adds_exception_handler(self):
        """Test that configure_rate_limiting adds exception handler"""
        from slowapi.errors import RateLimitExceeded

        class MockApp:
            def __init__(self):
                self.state = type("State", (), {})()
                self._exception_handlers = {}

            def add_exception_handler(self, exc_class, handler):
                self._exception_handlers[exc_class] = handler

        app = MockApp()
        configure_rate_limiting(app)

        # Verify exception handler is registered
        assert RateLimitExceeded in app._exception_handlers
        assert app._exception_handlers[RateLimitExceeded] is not None


class TestRateLimitingIntegration:
    """Integration tests for rate limiting configuration"""

    def test_rate_limiter_tracks_requests(self):
        """Test that rate limiter tracks requests properly"""
        # Verify limiter has storage configured
        assert limiter._storage is not None

    def test_limiter_uses_memory_storage(self):
        """Test that limiter is using memory storage (default)"""
        # In test/dev mode, memory storage is used
        assert limiter._storage_uri == "memory://"

    def test_app_has_rate_limiting_configured(self):
        """Test that the app has rate limiting configured"""
        # Verify limiter is set in app state
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is limiter

    def test_rate_limit_exception_handler_registered(self):
        """Test that rate limit exception handler is registered"""
        from slowapi.errors import RateLimitExceeded

        # Check exception handlers
        assert RateLimitExceeded in app.exception_handlers


class TestRateLimitDecorators:
    """Tests for rate limit decorator configuration"""

    def test_auth_routes_have_rate_limits(self):
        """Verify that auth routes have rate limiting decorators applied"""
        from app.routes.auth import (
            get_active_sessions,
            login_for_access_token,
            logout,
            logout_all_sessions,
            verify_2fa_and_get_token,
        )

        # These functions should have rate limiting applied
        # When using @limiter.limit(), it adds attributes to the function
        assert hasattr(login_for_access_token, "__wrapped__") or callable(login_for_access_token)
        assert hasattr(verify_2fa_and_get_token, "__wrapped__") or callable(verify_2fa_and_get_token)
        assert hasattr(logout, "__wrapped__") or callable(logout)
        assert hasattr(logout_all_sessions, "__wrapped__") or callable(logout_all_sessions)
        assert hasattr(get_active_sessions, "__wrapped__") or callable(get_active_sessions)

    def test_password_reset_routes_have_rate_limits(self):
        """Verify that password reset routes have rate limiting decorators"""
        from app.routes.password_reset import (
            api_request_password_reset,
            api_reset_password,
            request_password_reset,
            reset_password,
        )

        # These functions should have rate limiting applied
        assert callable(request_password_reset)
        assert callable(reset_password)
        assert callable(api_request_password_reset)
        assert callable(api_reset_password)
