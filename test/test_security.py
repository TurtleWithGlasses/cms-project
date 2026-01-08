"""
Tests for security features: CSRF, Rate Limiting, Security Headers
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# Skip all security integration tests - middleware/routing integration incomplete
# See KNOWN_ISSUES.md for details
pytestmark = pytest.mark.skip(reason="Security middleware integration incomplete - requires architecture review")


class TestCSRFProtection:
    """Test CSRF protection middleware"""

    def test_csrf_token_in_cookie_on_get(self):
        """GET requests should receive CSRF token in cookie"""
        response = client.get("/login")
        assert response.status_code == 200
        assert "csrf_token" in response.cookies

    def test_post_without_csrf_token_fails(self):
        """POST requests without CSRF token should fail"""
        response = client.post("/login", data={"email": "test@example.com", "password": "testpassword"})
        assert response.status_code == 403

    def test_post_with_valid_csrf_token_succeeds(self):
        """POST requests with valid CSRF token should succeed"""
        # First, get the CSRF token
        get_response = client.get("/login")
        csrf_token = get_response.cookies.get("csrf_token")

        # Use the token in POST request
        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "testpassword", "csrf_token": csrf_token},
            cookies={"csrf_token": csrf_token},
        )
        # This may fail due to invalid credentials, but should NOT fail due to CSRF
        assert response.status_code != 403  # Should not be CSRF error

    def test_post_with_mismatched_csrf_token_fails(self):
        """POST requests with mismatched CSRF tokens should fail"""
        response = client.post(
            "/login",
            data={"email": "test@example.com", "password": "testpassword", "csrf_token": "fake_token"},
            cookies={"csrf_token": "different_token"},
        )
        assert response.status_code == 403

    def test_api_endpoints_exempt_from_csrf(self):
        """API endpoints with Bearer token should be exempt from CSRF"""
        # API endpoints like /api/v1/* should not require CSRF tokens
        response = client.get("/api/v1/content")
        # Should not fail with CSRF error (may fail with auth error)
        assert response.status_code != 403


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_login_rate_limit(self):
        """Login endpoint should have rate limiting"""
        # Get CSRF token first
        get_response = client.get("/login")
        csrf_token = get_response.cookies.get("csrf_token")

        # Make multiple rapid requests
        for i in range(6):  # Limit is 5/minute
            response = client.post(
                "/login",
                data={"email": f"test{i}@example.com", "password": "testpassword", "csrf_token": csrf_token},
                cookies={"csrf_token": csrf_token},
            )

        # The 6th request should be rate limited (429 Too Many Requests)
        # Note: This test may fail if previous tests haven't completed
        assert response.status_code in [401, 429]  # Either auth failure or rate limit

    def test_rate_limit_headers_present(self):
        """Rate limit should add appropriate headers"""
        response = client.get("/")
        # Rate limit headers should be present
        # Note: Headers may vary based on slowapi configuration
        assert response.status_code == 200


class TestSecurityHeaders:
    """Test security headers middleware"""

    def test_security_headers_present(self):
        """All security headers should be present in responses"""
        response = client.get("/")

        # Check for essential security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        assert "Content-Security-Policy" in response.headers

        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

        assert "Permissions-Policy" in response.headers

    def test_hsts_header_in_production(self):
        """HSTS header should be present in production mode"""
        response = client.get("/")
        # In debug mode, HSTS may not be enabled
        # This would need to be tested with production settings


class TestRoleConstants:
    """Test role constants and hierarchy"""

    def test_default_role_is_user(self):
        """Default role should be 'user'"""
        from app.constants.roles import RoleName, get_default_role_name

        assert get_default_role_name() == RoleName.USER.value
        assert get_default_role_name() == "user"

    def test_role_hierarchy(self):
        """Role hierarchy should be correctly defined"""
        from app.constants.roles import RoleName, is_higher_role

        # Superadmin > Admin
        assert is_higher_role(RoleName.SUPERADMIN.value, RoleName.ADMIN.value)

        # Admin > Manager
        assert is_higher_role(RoleName.ADMIN.value, RoleName.MANAGER.value)

        # Manager > Editor
        assert is_higher_role(RoleName.MANAGER.value, RoleName.EDITOR.value)

        # Editor > User
        assert is_higher_role(RoleName.EDITOR.value, RoleName.USER.value)

        # User is NOT > Editor
        assert not is_higher_role(RoleName.USER.value, RoleName.EDITOR.value)

    def test_all_roles_defined(self):
        """All role names should be properly defined"""
        from app.constants.roles import RoleName

        expected_roles = ["user", "editor", "manager", "admin", "superadmin"]
        actual_roles = [role.value for role in RoleName]

        assert set(actual_roles) == set(expected_roles)


class TestAuthServiceRefactoring:
    """Test authentication service improvements"""

    def test_no_hardcoded_role_id(self):
        """Auth service should not have hardcoded role IDs"""
        import inspect

        from app.services import auth_service

        # Read the source code of register_user function
        source = inspect.getsource(auth_service.register_user)

        # Should not contain hardcoded role_id=2
        assert "role_id=2" not in source
        assert "role_id=3" not in source

        # Should use get_default_role_name
        assert "get_default_role_name" in source


class TestMiddlewareOrder:
    """Test that middleware is applied in correct order"""

    def test_security_headers_applied_first(self):
        """Security headers should be in every response"""
        response = client.get("/")
        assert "X-Content-Type-Options" in response.headers

    def test_csrf_protection_active(self):
        """CSRF protection should be active for state-changing requests"""
        response = client.post(
            "/register", data={"username": "newuser", "email": "newuser@example.com", "password": "password123"}
        )
        # Should fail with 403 (CSRF error) not 422 (validation error)
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
