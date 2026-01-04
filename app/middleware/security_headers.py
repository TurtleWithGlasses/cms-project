"""
Security Headers Middleware for FastAPI

This middleware adds security headers to all HTTP responses to protect
against common web vulnerabilities.
"""

from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter in older browsers
    - Strict-Transport-Security: Enforce HTTPS (production only)
    - Content-Security-Policy: Control resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = None,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp_policy: str = None,
    ):
        super().__init__(app)
        # HSTS should only be enabled in production over HTTPS
        self.enable_hsts = enable_hsts if enable_hsts is not None else not settings.debug
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload

        # Default Content Security Policy
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response."""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp_policy

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # HTTP Strict Transport Security (HSTS) - only in production
        if self.enable_hsts:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Remove server identification header (if present)
        if "Server" in response.headers:
            del response.headers["Server"]

        return response
