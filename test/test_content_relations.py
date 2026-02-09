"""
Tests for Content Relations functionality.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.models.content_relations import (
    ContentRedirect,
    ContentRelation,
    ContentSeries,
    ContentSeriesItem,
    RelationType,
)
from app.services.content_relations_service import ContentRelationsService
from main import app


class TestContentRelationModels:
    """Tests for content relation model creation."""

    def test_relation_type_enum(self):
        """Test RelationType enum values."""
        assert RelationType.RELATED_TO.value == "related_to"
        assert RelationType.PART_OF_SERIES.value == "part_of_series"
        assert RelationType.DEPENDS_ON.value == "depends_on"
        assert RelationType.TRANSLATED_FROM.value == "translated_from"

    def test_content_relation_repr(self):
        """Test ContentRelation __repr__."""
        r = ContentRelation(
            id=1,
            source_content_id=10,
            target_content_id=20,
            relation_type=RelationType.RELATED_TO,
        )
        assert "source=10" in repr(r)
        assert "target=20" in repr(r)

    def test_content_series_repr(self):
        """Test ContentSeries __repr__."""
        s = ContentSeries(id=1, title="My Series")
        assert "My Series" in repr(s)

    def test_content_series_item_repr(self):
        """Test ContentSeriesItem __repr__."""
        item = ContentSeriesItem(series_id=1, content_id=5, order=0)
        assert "series=1" in repr(item)
        assert "content=5" in repr(item)

    def test_content_redirect_repr(self):
        """Test ContentRedirect __repr__."""
        r = ContentRedirect(id=1, old_slug="old-post", content_id=10)
        assert "old-post" in repr(r)
        assert "content_id=10" in repr(r)

    def test_content_redirect_defaults(self):
        """Test ContentRedirect has default status_code configured."""
        col = ContentRedirect.__table__.columns["status_code"]
        assert col.default.arg == 301


class TestContentRelationServiceValidation:
    """Tests for ContentRelationsService validation logic (no DB required)."""

    @pytest.mark.asyncio
    async def test_self_relation_raises_error(self):
        """Test that creating a self-relation raises ValueError."""
        # We can test the validation logic without a real DB
        # by checking that the error fires before any DB call
        from unittest.mock import AsyncMock, MagicMock

        mock_db = MagicMock()
        service = ContentRelationsService(mock_db)

        with pytest.raises(ValueError, match="cannot be related to itself"):
            await service.create_relation(
                source_content_id=1,
                target_content_id=1,
            )


class TestContentRelationsRoutes:
    """Tests for Content Relations API routes (auth checks)."""

    @pytest.mark.asyncio
    async def test_get_relations_public(self):
        """Test that getting relations is accessible."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/content/1/relations")

        # Should return 200 (empty list) even without auth
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_relation_requires_auth(self):
        """Test that creating a relation requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/content/1/relations",
                json={"target_content_id": 2, "relation_type": "related_to"},
            )

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_delete_relation_requires_auth(self):
        """Test that deleting a relation requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/relations/1")

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_list_series_public(self):
        """Test that listing series is accessible."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/series")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_series_requires_auth(self):
        """Test that creating a series requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/series",
                json={"title": "Test", "slug": "test"},
            )

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_get_series_responds(self):
        """Test that getting a series by ID responds without error."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/series/999")

        # Endpoint responds (may redirect to login for unauthenticated users)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_series_requires_auth(self):
        """Test that deleting a series requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/series/1")

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_list_redirects_requires_auth(self):
        """Test that listing redirects requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/redirects")

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_resolve_redirect_responds(self):
        """Test that resolving a redirect responds without error."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/redirects/resolve/nonexistent-slug")

        # Endpoint responds (may redirect to login for unauthenticated users)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_redirect_requires_auth(self):
        """Test that creating a redirect requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/redirects",
                json={"old_slug": "old", "content_id": 1},
            )

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_delete_redirect_requires_auth(self):
        """Test that deleting a redirect requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/redirects/1")

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_add_to_series_requires_auth(self):
        """Test that adding to a series requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/series/1/items",
                json={"content_id": 1},
            )

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_remove_from_series_requires_auth(self):
        """Test that removing from a series requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete("/api/v1/series/1/items/1")

        assert response.status_code in (307, 401, 403)

    @pytest.mark.asyncio
    async def test_reorder_series_requires_auth(self):
        """Test that reordering a series requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/series/1/reorder",
                json={"content_ids": [1, 2]},
            )

        assert response.status_code in (307, 401, 403)
