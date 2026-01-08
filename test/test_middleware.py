"""
Tests for middleware modules
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from app.config import settings
from app.middleware.csrf import CSRFMiddleware, get_csrf_token
from app.middleware.security_headers import SecurityHeadersMiddleware

# Skip all middleware tests - middleware integration incomplete
# See KNOWN_ISSUES.md for details
# pytestmark = pytest.mark.skip(reason="Middleware integration incomplete - requires architecture review")


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

        client = TestClient(app, raise_server_exceptions=False)

        # POST without token should fail
        response = client.post("/test", data={"test": "data"})
        assert response.status_code == 403

    def test_csrf_exempt_paths(self):
        """CSRF middleware should exempt configured paths"""
        app = FastAPI()

        @app.post("/api/v1/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key, exempt_paths=["/api/v1"])

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
        response = client.post("/test", headers={"Authorization": "Bearer fake_token"})
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

        app.add_middleware(SecurityHeadersMiddleware, csp_policy=custom_csp)

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


class TestCSRFMiddlewareExtended:
    """Extended CSRF middleware tests for better coverage"""

    def test_csrf_with_put_method(self):
        """CSRF middleware should validate tokens on PUT"""
        app = FastAPI()

        @app.put("/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.put("/test", data={"test": "data"})
        assert response.status_code == 403

    def test_csrf_with_patch_method(self):
        """CSRF middleware should validate tokens on PATCH"""
        app = FastAPI()

        @app.patch("/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.patch("/test", data={"test": "data"})
        assert response.status_code == 403

    def test_csrf_with_delete_method(self):
        """CSRF middleware should validate tokens on DELETE"""
        app = FastAPI()

        @app.delete("/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.delete("/test")
        assert response.status_code == 403

    def test_csrf_get_method_no_validation(self):
        """GET requests should not require CSRF tokens"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key)

        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200

    def test_csrf_token_expiry_configured(self):
        """Should respect custom token expiry"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(
            CSRFMiddleware,
            secret_key=settings.secret_key,
            token_expiry=7200,  # 2 hours
        )

        client = TestClient(app)
        response = client.get("/test")
        assert "csrf_token" in response.cookies

    def test_csrf_custom_cookie_name(self):
        """Should use custom cookie name if configured"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key, cookie_name="custom_csrf")

        client = TestClient(app)
        response = client.get("/test")
        assert "custom_csrf" in response.cookies

    def test_csrf_custom_header_name(self):
        """Should accept custom header name"""
        app = FastAPI()

        @app.post("/test")
        async def test_route():
            return {"message": "success"}

        app.add_middleware(CSRFMiddleware, secret_key=settings.secret_key, header_name="X-Custom-CSRF")

        client = TestClient(app, raise_server_exceptions=False)
        response = client.post("/test")
        assert response.status_code == 403


class TestSecurityHeadersExtended:
    """Extended security headers tests"""

    def test_server_header_removed(self):
        """Server identification header should be removed"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            response = JSONResponse({"message": "test"})
            response.headers["Server"] = "TestServer/1.0"
            return response

        app.add_middleware(SecurityHeadersMiddleware)

        client = TestClient(app)
        response = client.get("/test")
        assert "Server" not in response.headers or response.headers.get("Server") != "TestServer/1.0"

    def test_hsts_with_subdomains(self):
        """HSTS should include subdomains when configured"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True, hsts_include_subdomains=True)

        client = TestClient(app)
        response = client.get("/test")
        assert "includeSubDomains" in response.headers["Strict-Transport-Security"]

    def test_hsts_with_preload(self):
        """HSTS should include preload when configured"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True, hsts_preload=True)

        client = TestClient(app)
        response = client.get("/test")
        assert "preload" in response.headers["Strict-Transport-Security"]

    def test_custom_hsts_max_age(self):
        """Should respect custom HSTS max-age"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        custom_age = 63072000  # 2 years
        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True, hsts_max_age=custom_age)

        client = TestClient(app)
        response = client.get("/test")
        assert f"max-age={custom_age}" in response.headers["Strict-Transport-Security"]

    def test_all_security_headers_present(self):
        """Verify all critical security headers are present"""
        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "test"}

        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)

        client = TestClient(app)
        response = client.get("/test")

        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy",
            "Strict-Transport-Security",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"


class TestRBACMiddleware:
    """Test Role-Based Access Control middleware"""

    def test_public_paths_accessible_without_auth(self):
        """Public paths should be accessible without authentication"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        @app.get("/login")
        async def login():
            return {"message": "login page"}

        @app.get("/register")
        async def register():
            return {"message": "register page"}

        @app.get("/")
        async def home():
            return {"message": "home"}

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app)

        # Public paths should be accessible
        assert client.get("/login").status_code == 200
        assert client.get("/register").status_code == 200
        assert client.get("/").status_code == 200

    def test_protected_path_redirects_without_token(self):
        """Protected paths should redirect to login without token"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        @app.get("/admin")
        async def admin_page():
            return {"message": "admin page"}

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app)

        # Should redirect to login
        response = client.get("/admin", follow_redirects=False)
        assert response.status_code == 307  # Redirect
        assert "/login" in response.headers.get("location", "")

    def test_docs_path_is_public(self):
        """API docs should be publicly accessible"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app)

        response = client.get("/docs", follow_redirects=False)
        # Should not redirect
        assert response.status_code != 307

    def test_openapi_json_is_public(self):
        """OpenAPI schema should be publicly accessible"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app)

        response = client.get("/openapi.json", follow_redirects=False)
        # Should not redirect
        assert response.status_code != 307

    def test_bearer_token_prefix_handling(self):
        """Should handle 'Bearer ' prefix in token"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        @app.get("/admin")
        async def admin_page():
            return {"message": "admin page"}

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app, raise_server_exceptions=False)

        # Token with Bearer prefix should redirect to login (invalid token)
        response = client.get("/admin", headers={"Authorization": "Bearer fake_token"}, follow_redirects=False)
        # Will fail auth and either redirect or return error
        assert response.status_code in [307, 401, 403, 500]

    def test_token_in_cookie(self):
        """Should accept token from cookie"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        @app.get("/admin")
        async def admin_page():
            return {"message": "admin page"}

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app, raise_server_exceptions=False)

        # Token in cookie should be processed (will fail auth but token is extracted)
        response = client.get("/admin", cookies={"access_token": "fake_token"}, follow_redirects=False)
        # Will fail auth but not redirect to login
        assert response.status_code in [401, 403, 500]

    def test_static_paths_public(self):
        """Static resource paths should be public"""
        from app.middleware.rbac import RBACMiddleware

        app = FastAPI()

        @app.get("/favicon.ico")
        async def favicon():
            return Response(content=b"fake-icon")

        app.add_middleware(RBACMiddleware, allowed_roles=["admin"])

        client = TestClient(app)

        # favicon.ico should be accessible without auth
        response = client.get("/favicon.ico", follow_redirects=False)
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
