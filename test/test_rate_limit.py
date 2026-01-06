"""
Tests for rate limiting middleware

Tests rate limiter configuration and functionality.
"""

from slowapi import Limiter

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
