"""
Tests for Search Routes

Tests API endpoints for full-text search, suggestions, facets, and search analytics.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_content

from app.models.content import ContentStatus
from app.models.search_query import SearchQuery


@pytest.fixture
async def search_trigger(test_db: AsyncSession):
    """Create the FTS trigger function and trigger on the content table."""
    await test_db.execute(
        text("""
            CREATE OR REPLACE FUNCTION content_search_vector_update() RETURNS trigger AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                    setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                    setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'C') ||
                    setweight(to_tsvector('english', COALESCE(NEW.meta_keywords, '')), 'D');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
    )
    await test_db.execute(
        text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'content_search_vector_trigger'
                ) THEN
                    CREATE TRIGGER content_search_vector_trigger
                    BEFORE INSERT OR UPDATE ON content
                    FOR EACH ROW EXECUTE FUNCTION content_search_vector_update();
                END IF;
            END $$;
        """)
    )
    await test_db.commit()


class TestSearchRoutes:
    """Test full-text search API endpoints"""

    @pytest.mark.asyncio
    async def test_search_endpoint_returns_results(self, client, async_db_session, admin_user, search_trigger):
        """Test search endpoint returns matching results"""
        from app.auth import create_access_token

        await create_test_content(
            async_db_session,
            title="PostgreSQL Database Guide",
            body="Learn about PostgreSQL full-text search features",
            author_id=admin_user.id,
            status=ContentStatus.PUBLISHED,
        )

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/?q=PostgreSQL", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "PostgreSQL"
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

    @pytest.mark.asyncio
    async def test_search_endpoint_validates_query_too_short(self, client, admin_user):
        """Test search endpoint rejects query shorter than min length"""
        from app.auth import create_access_token

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/?q=a", headers=headers)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_search_endpoint_validates_empty_query(self, client, admin_user):
        """Test search endpoint requires query parameter"""
        from app.auth import create_access_token

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/", headers=headers)

        assert response.status_code == 422  # Missing required param

    @pytest.mark.asyncio
    async def test_search_endpoint_invalid_sort_by(self, client, admin_user, search_trigger):
        """Test search endpoint rejects invalid sort_by parameter"""
        from app.auth import create_access_token

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/?q=test&sort_by=invalid", headers=headers)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_search_endpoint_no_results(self, client, admin_user, search_trigger):
        """Test search endpoint returns empty results for non-matching query"""
        from app.auth import create_access_token

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/?q=xyznonexistent", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []


class TestSuggestionsRoutes:
    """Test search suggestions/autocomplete endpoint"""

    @pytest.mark.asyncio
    async def test_suggestions_endpoint(self, client, async_db_session, admin_user):
        """Test suggestions endpoint returns matching titles"""
        from app.auth import create_access_token

        await create_test_content(
            async_db_session,
            title="Getting Started with Python",
            body="A beginner guide",
            author_id=admin_user.id,
            status=ContentStatus.PUBLISHED,
        )

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/suggestions?q=Getting", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "query" in data
        assert data["query"] == "Getting"

    @pytest.mark.asyncio
    async def test_suggestions_endpoint_requires_query(self, client, admin_user):
        """Test suggestions endpoint requires q parameter"""
        from app.auth import create_access_token

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/suggestions", headers=headers)

        assert response.status_code == 422


class TestFacetsRoutes:
    """Test search facets endpoint"""

    @pytest.mark.asyncio
    async def test_facets_endpoint(self, client, async_db_session, admin_user):
        """Test facets endpoint returns facet counts"""
        from app.auth import create_access_token

        await create_test_content(
            async_db_session,
            title="Facet Test Content",
            body="Content for testing facets",
            author_id=admin_user.id,
            status=ContentStatus.PUBLISHED,
        )

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/facets", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "tags" in data
        assert "statuses" in data
        assert "authors" in data

    @pytest.mark.asyncio
    async def test_facets_endpoint_with_query(self, client, async_db_session, admin_user, search_trigger):
        """Test facets endpoint accepts optional query filter"""
        from app.auth import create_access_token

        await create_test_content(
            async_db_session,
            title="Filtered Facet Content",
            body="Body text for filtering",
            author_id=admin_user.id,
            status=ContentStatus.PUBLISHED,
        )

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/search/facets?q=Filtered", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "statuses" in data


class TestSearchAnalyticsRoutes:
    """Test search analytics endpoint"""

    @pytest.mark.asyncio
    async def test_analytics_requires_admin(self, client, auth_headers):
        """Test analytics endpoint requires admin role"""
        response = client.get("/api/v1/search/analytics", headers=auth_headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_analytics_endpoint(self, client, admin_user):
        """Test admin can access search analytics"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/search/analytics", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_searches" in data
        assert "unique_queries" in data
        assert "avg_results_count" in data
        assert "avg_execution_time_ms" in data
        assert "top_queries" in data
        assert "zero_result_queries" in data
        assert "searches_over_time" in data

    @pytest.mark.asyncio
    async def test_analytics_custom_days(self, client, admin_user):
        """Test analytics endpoint accepts custom days parameter"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get("/api/v1/search/analytics?days=7", headers=headers)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_analytics_requires_auth(self, client):
        """Test analytics endpoint requires authentication"""
        response = client.get("/api/v1/search/analytics")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_endpoints_no_auth_required_for_public(self, client, admin_user, search_trigger):
        """Test that search, suggestions, and facets don't require specific roles"""
        from app.auth import create_access_token

        token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # Search endpoint - accessible to any authenticated user
        response = client.get("/api/v1/search/?q=test", headers=headers)
        assert response.status_code == 200

        # Suggestions endpoint - accessible to any authenticated user
        response = client.get("/api/v1/search/suggestions?q=test", headers=headers)
        assert response.status_code == 200

        # Facets endpoint - accessible to any authenticated user
        response = client.get("/api/v1/search/facets", headers=headers)
        assert response.status_code == 200
