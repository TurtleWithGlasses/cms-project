"""
Tests for middleware modules
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi import Request, Response, FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse
from app.middleware.csrf import CSRFMiddleware, get_csrf_token
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.config import settings


class TestCSRFMiddleware:
    """Test CSRF middleware functionality"""

    def test_csrf_token_generation(self):
        """CSRF middleware should generate valid tokens"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app)
        response = client.get("/test")

        assert "csrf_token" in response.cookies
        assert len(response.cookies["csrf_token"]) > 0

    def test_csrf_token_validation_post(self):
        """CSRF middleware should validate tokens on POST"""
        app = FastAPI()

        @app.post("/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app)

        # POST without token should fail
        response = client.post("/test", data={"test": "data"})
        assert response.status_code == 403

    def test_csrf_exempt_paths(self):
        """CSRF middleware should exempt configured paths"""
        app = FastAPI()

        @app.post("/api/v1/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(
            CSRFMiddleware,
            secret_key=settings.secret_key,
            exempt_paths=["/api/v1"]
        )

        client = TestClient(app)

        # POST to exempt path should work without CSRF token
        response = client.post("/api/v1/test")
        # May fail for other reasons but not CSRF (403)
        assert response.status_code != 403

    def test_csrf_bearer_token_exempt(self):
        """Requests with Bearer tokens should be exempt"""
        app = FastAPI()

        @app.post("/test")
        async def test_route(request: Request):
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app)

        # POST with Bearer token should bypass CSRF
        response = client.post(
            "/test",
            headers={"Authorization": "Bearer fake_token"}
        )
        # Should not fail with CSRF error
        assert response.status_code != 403 or "CSRF" not in str(response.content)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware"""

    def test_security_headers_added(self):
        """Security headers should be added to responses"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware)

        client = TestClient(app)
        response = client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    def test_hsts_enabled_in_production(self):
        """HSTS should be enabled when configured"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)

        client = TestClient(app)
        response = client.get("/test")

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=" in response.headers["Strict-Transport-Security"]

    def test_hsts_disabled_by_default(self):
        """HSTS should be disabled in debug mode"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=False)

        client = TestClient(app)
        response = client.get("/test")

        assert "Strict-Transport-Security" not in response.headers

    def test_custom_csp_policy(self):
        """Should allow custom CSP policy"""
        custom_csp = "default-src 'none'; script-src 'self'"
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(
            SecurityHeadersMiddleware,
            csp_policy=custom_csp
        )

        client = TestClient(app)
        response = client.get("/test")

        assert response.headers["Content-Security-Policy"] == custom_csp


class TestGetCSRFToken:
    """Test CSRF token helper function"""

    def test_get_csrf_token_from_state(self):
        """Should get CSRF token from request state"""
        from starlette.requests import Request as StarletteRequest

        # Create a mock request with state
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }
        request = StarletteRequest(scope)
        request.state.csrf_token = "test_token_123"

        token = get_csrf_token(request)
        assert token == "test_token_123"

    def test_get_csrf_token_from_cookies(self):
        """Should fall back to cookies if state not available"""
        from starlette.requests import Request as StarletteRequest

        # Create a mock request with cookies
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [(b"cookie", b"csrf_token=cookie_token_456")],
        }
        request = StarletteRequest(scope)

        token = get_csrf_token(request)
        assert token == "cookie_token_456"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
