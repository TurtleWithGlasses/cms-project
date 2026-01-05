"""
Rate Limiting Middleware for FastAPI

This middleware provides rate limiting to protect against brute force attacks
and API abuse.
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/hour"],  # Global default limit
    storage_uri="memory://",  # Use memory storage (upgrade to Redis for production)
    headers_enabled=True,  # Include rate limit headers in responses
)


def get_rate_limiter():
    """Get the rate limiter instance."""
    return limiter


def configure_rate_limiting(app):
    """
    Configure rate limiting for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
