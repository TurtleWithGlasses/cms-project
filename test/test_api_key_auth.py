"""
Tests for Phase 4.1: API key authentication dependency and RBAC middleware update.
"""

import inspect

import pytest

# ============================================================================
# TestApiKeyAuthDependency — auth.py additions
# ============================================================================


class TestApiKeyAuthDependency:
    def test_get_current_user_from_api_key_exists(self):
        from app.auth import get_current_user_from_api_key

        assert callable(get_current_user_from_api_key)

    def test_get_current_user_from_api_key_is_coroutine(self):
        from app.auth import get_current_user_from_api_key

        assert inspect.iscoroutinefunction(get_current_user_from_api_key)

    def test_get_current_user_any_auth_exists(self):
        from app.auth import get_current_user_any_auth

        assert callable(get_current_user_any_auth)

    def test_get_current_user_any_auth_is_coroutine(self):
        from app.auth import get_current_user_any_auth

        assert inspect.iscoroutinefunction(get_current_user_any_auth)


# ============================================================================
# TestApiKeyAnyAuth — combined auth logic
# ============================================================================


class TestApiKeyAnyAuth:
    def test_any_auth_raises_without_credentials(self):
        """get_current_user_any_auth must raise when neither JWT nor API key is present."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import HTTPException

        from app.auth import get_current_user_any_auth

        # Request with no cookies and no Authorization/X-API-Key headers
        mock_request = MagicMock()
        mock_request.cookies = {}
        mock_request.headers = {}

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_current_user_any_auth(request=mock_request, db=mock_db))
        assert exc_info.value.status_code == 401

    def test_any_auth_signature_has_request_and_db(self):
        from app.auth import get_current_user_any_auth

        sig = inspect.signature(get_current_user_any_auth)
        assert "request" in sig.parameters
        assert "db" in sig.parameters

    def test_api_key_auth_signature_has_request_and_db(self):
        from app.auth import get_current_user_from_api_key

        sig = inspect.signature(get_current_user_from_api_key)
        assert "request" in sig.parameters
        assert "db" in sig.parameters


# ============================================================================
# TestRBACMiddlewareApiKey — RBAC middleware changes
# ============================================================================


class TestRBACMiddlewareApiKey:
    def test_graphql_in_public_paths(self):
        from unittest.mock import MagicMock

        from app.middleware.rbac import RBACMiddleware

        # Instantiate with a dummy app
        middleware = RBACMiddleware(MagicMock(), allowed_roles=["user", "admin"])
        assert "/graphql" in middleware.public_paths

    def test_rbac_source_handles_api_key_header(self):
        """Verify the RBAC middleware source references X-API-Key."""
        import inspect as ins

        from app.middleware import rbac as rbac_module

        source = ins.getsource(rbac_module)
        assert "X-API-Key" in source, "RBAC middleware must check X-API-Key header"

    def test_api_key_only_request_not_redirected(self):
        """Requests with only X-API-Key should not be redirected to /login."""
        from fastapi.testclient import TestClient

        from main import app

        # A request with an X-API-Key header should NOT return 307 to /login.
        # It may return 401/400 from route-level validation, but not a login redirect.
        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.get("/api/v1/content/", headers={"X-API-Key": "cms_test_invalidsecret"})
        # Should NOT be a redirect to /login
        assert response.status_code != 307, (
            f"API key requests should not redirect to /login, got {response.status_code}"
        )
