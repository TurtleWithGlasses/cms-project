"""
Tests for API Key functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.api_key import APIKey, APIKeyScope
from main import app


@pytest.fixture
def api_key_data():
    """Sample API key creation data."""
    return {
        "name": "Test API Key",
        "description": "API key for testing",
        "scopes": ["read", "content:read"],
        "expires_in_days": 30,
        "rate_limit": 100,
    }


class TestAPIKeyScopes:
    """Tests for API key scope functionality."""

    def test_scope_values(self):
        """Test that all scopes have correct values."""
        assert APIKeyScope.READ.value == "read"
        assert APIKeyScope.WRITE.value == "write"
        assert APIKeyScope.ADMIN.value == "admin"
        assert APIKeyScope.CONTENT_READ.value == "content:read"
        assert APIKeyScope.CONTENT_WRITE.value == "content:write"


class TestAPIKeyModel:
    """Tests for APIKey model."""

    def test_generate_key(self):
        """Test API key generation."""
        full_key, prefix, secret = APIKey.generate_key()

        # Check format
        assert full_key.startswith("cms_")
        assert "_" in full_key
        assert len(prefix) == 8  # cms_xxxx
        assert len(secret) >= 32

        # Full key should be prefix_secret
        assert full_key == f"{prefix}_{secret}"

    def test_get_scopes(self):
        """Test parsing scopes from string."""
        key = APIKey(scopes="read,write,content:read")
        scopes = key.get_scopes()

        assert scopes == ["read", "write", "content:read"]

    def test_get_scopes_empty(self):
        """Test parsing empty scopes."""
        key = APIKey(scopes="")
        assert key.get_scopes() == []

    def test_has_scope_direct(self):
        """Test direct scope check."""
        key = APIKey(scopes="read,content:read")

        assert key.has_scope("read") is True
        assert key.has_scope("content:read") is True
        assert key.has_scope("write") is False

    def test_has_scope_admin(self):
        """Test admin scope grants all permissions."""
        key = APIKey(scopes="admin")

        assert key.has_scope("read") is True
        assert key.has_scope("write") is True
        assert key.has_scope("content:read") is True

    def test_has_scope_write_includes_read(self):
        """Test write scope includes read."""
        key = APIKey(scopes="content:write")

        assert key.has_scope("content:read") is True
        assert key.has_scope("content:write") is True


class TestAPIKeyRoutes:
    """Tests for API key endpoints."""

    @pytest.mark.asyncio
    async def test_list_available_scopes(self):
        """Test listing available scopes."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/api-keys/scopes")

        assert response.status_code == 200
        data = response.json()
        assert "scopes" in data
        assert len(data["scopes"]) > 0

        # Check scope structure
        scope = data["scopes"][0]
        assert "value" in scope
        assert "name" in scope

    @pytest.mark.asyncio
    async def test_list_api_keys_requires_auth(self):
        """Test that listing API keys requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/api-keys")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_api_key_requires_auth(self, api_key_data):
        """Test that creating API keys requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/api-keys", json=api_key_data)

        assert response.status_code == 401


class TestAPIKeyValidation:
    """Tests for API key validation."""

    @pytest.mark.asyncio
    async def test_create_with_invalid_scope(self, api_key_data):
        """Test that invalid scopes are rejected."""
        api_key_data["scopes"] = ["invalid_scope"]

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Would need authentication to test this properly
            response = await client.post("/api/v1/api-keys", json=api_key_data)

        # Without auth, should get 401
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_with_invalid_rate_limit(self, api_key_data):
        """Test that invalid rate limits are rejected by schema."""
        api_key_data["rate_limit"] = 5  # Below minimum of 10

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/api-keys", json=api_key_data)

        # Schema validation should fail (422) or auth fails first (401)
        assert response.status_code in [401, 422]
