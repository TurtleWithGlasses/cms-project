"""
CSRF Protection Middleware for FastAPI

This middleware provides Cross-Site Request Forgery (CSRF) protection
for form submissions and state-changing operations.
"""

import secrets
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect against CSRF attacks.

    - Generates CSRF tokens for GET requests
    - Validates CSRF tokens for POST, PUT, PATCH, DELETE requests
    - Exempts safe methods (GET, HEAD, OPTIONS) from validation
    - Exempts API endpoints that use Bearer token authentication
    """

    def __init__(
        self,
        app,
        secret_key: str | None = None,
        token_name: str = "csrf_token",
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        exempt_paths: list[str] | None = None,
        token_expiry: int = 3600,  # 1 hour in seconds
    ):
        super().__init__(app)
        self.secret_key = secret_key or settings.secret_key
        self.token_name = token_name
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.token_expiry = token_expiry
        self.serializer = URLSafeTimedSerializer(self.secret_key)

        # Default exempt paths (API endpoints, auth endpoints)
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1",
            "/auth/token",
        ]

    def _is_exempt(self, path: str) -> bool:
        """Check if the path is exempt from CSRF protection."""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    def _generate_token(self) -> str:
        """Generate a new CSRF token."""
        random_string = secrets.token_urlsafe(32)
        return self.serializer.dumps(random_string)

    def _validate_token(self, token: str) -> bool:
        """Validate a CSRF token."""
        try:
            self.serializer.loads(token, max_age=self.token_expiry)
            return True
        except (BadSignature, SignatureExpired):
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and validate CSRF tokens."""

        # Safe methods don't need CSRF protection
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)

            # Generate and set CSRF token in cookie for safe methods
            if not self._is_exempt(request.url.path):
                csrf_token = self._generate_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=csrf_token,
                    httponly=True,
                    samesite="lax",
                    secure=not settings.debug,  # Use secure cookies in production
                )
                # Make token available to request state for templates
                request.state.csrf_token = csrf_token

            return response

        # Check if path is exempt from CSRF protection
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Check if request uses Bearer token authentication (API endpoints)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # API endpoints with Bearer tokens are exempt
            return await call_next(request)

        # For state-changing methods, validate CSRF token
        # Check token in header first, then form data
        token_from_header = request.headers.get(self.header_name)
        token_from_cookie = request.cookies.get(self.cookie_name)

        # Try to get token from form data
        token_from_form = None
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                # We need to get the form data
                form_data = await request.form()
                token_from_form = form_data.get(self.token_name)
                # Store form data in request state for later use
                request.state._form = form_data

        # Use token from header or form
        submitted_token = token_from_header or token_from_form

        if not submitted_token:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")

        # Ensure submitted_token is a string (not UploadFile)
        if not isinstance(submitted_token, str):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token must be a string")

        if not token_from_cookie:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF cookie missing")

        # Validate that submitted token matches cookie token
        if submitted_token != token_from_cookie:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")

        # Validate token signature and expiry
        if not self._validate_token(submitted_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid or expired")

        response = await call_next(request)
        return response


def get_csrf_token(request: Request) -> str:
    """
    Helper function to get CSRF token from request state.
    Use this in templates to render the CSRF token.
    """
    return getattr(request.state, "csrf_token", request.cookies.get("csrf_token", ""))
