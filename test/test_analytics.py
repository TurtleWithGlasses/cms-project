"""
Tests for Analytics & Metrics functionality (Phase 3.2).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content, ContentStatus
from app.models.content_view import ContentView
from app.models.user import User
from app.services.analytics_service import AnalyticsService


@pytest.fixture
async def test_content(test_db: AsyncSession, test_user: User) -> Content:
    """Create test content for analytics."""
    content = Content(
        title="Analytics Test Article",
        body="This is test content for analytics testing with enough words to estimate read time.",
        slug="analytics-test-article",
        status=ContentStatus.PUBLISHED,
        author_id=test_user.id,
    )
    test_db.add(content)
    await test_db.commit()
    await test_db.refresh(content)
    return content


class TestContentViewModel:
    """Tests for ContentView model."""

    @pytest.mark.asyncio
    async def test_content_view_creation(self, test_db: AsyncSession, test_content: Content, test_user: User):
        """Test creating a ContentView record."""
        view = ContentView(
            content_id=test_content.id,
            user_id=test_user.id,
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
            referrer="https://example.com",
        )
        test_db.add(view)
        await test_db.commit()
        await test_db.refresh(view)

        assert view.id is not None
        assert view.content_id == test_content.id
        assert view.user_id == test_user.id
        assert view.ip_address == "192.168.1.1"
        assert view.created_at is not None

    @pytest.mark.asyncio
    async def test_content_view_table_defaults(self):
        """Test ContentView table column defaults."""
        columns = ContentView.__table__.columns
        assert columns["user_id"].nullable is True
        assert columns["ip_address"].nullable is True
        assert columns["duration_seconds"].nullable is True
        assert columns["created_at"].nullable is False


class TestAnalyticsService:
    """Tests for AnalyticsService methods."""

    def test_estimate_read_time_short(self):
        """Test read time for short content (minimum 1 minute)."""
        body = "Hello world"
        result = AnalyticsService.estimate_read_time(body)
        assert result == 1

    def test_estimate_read_time_long(self):
        """Test read time for longer content."""
        # 400 words -> 2 minutes
        body = " ".join(["word"] * 400)
        result = AnalyticsService.estimate_read_time(body)
        assert result == 2

    def test_estimate_read_time_exact(self):
        """Test read time rounds up correctly."""
        # 201 words -> ceil(201/200) = 2 minutes
        body = " ".join(["word"] * 201)
        result = AnalyticsService.estimate_read_time(body)
        assert result == 2

    @pytest.mark.asyncio
    async def test_record_content_view(self, test_db: AsyncSession, test_content: Content):
        """Test recording a content view."""
        recorded = await AnalyticsService.record_content_view(
            db=test_db,
            content_id=test_content.id,
            ip_address="10.0.0.1",
            user_agent="TestBrowser/1.0",
        )
        assert recorded is True

    @pytest.mark.asyncio
    async def test_record_content_view_dedup(self, test_db: AsyncSession, test_content: Content):
        """Test view deduplication within 30-minute window."""
        # First view
        recorded1 = await AnalyticsService.record_content_view(
            db=test_db,
            content_id=test_content.id,
            ip_address="10.0.0.2",
        )
        assert recorded1 is True

        # Second view from same IP within 30 minutes — should be deduplicated
        recorded2 = await AnalyticsService.record_content_view(
            db=test_db,
            content_id=test_content.id,
            ip_address="10.0.0.2",
        )
        assert recorded2 is False

    @pytest.mark.asyncio
    async def test_get_content_view_stats(self, test_db: AsyncSession, test_content: Content):
        """Test getting view stats for content."""
        # Record a view
        await AnalyticsService.record_content_view(
            db=test_db,
            content_id=test_content.id,
            ip_address="10.0.0.3",
        )

        stats = await AnalyticsService.get_content_view_stats(
            db=test_db,
            content_id=test_content.id,
        )

        assert stats["content_id"] == test_content.id
        assert stats["total_views"] >= 1
        assert "unique_visitors" in stats
        assert "daily_views" in stats

    @pytest.mark.asyncio
    async def test_get_popular_content(self, test_db: AsyncSession, test_content: Content):
        """Test getting popular content ranking."""
        # Record views
        await AnalyticsService.record_content_view(
            db=test_db,
            content_id=test_content.id,
            ip_address="10.0.0.4",
        )

        popular = await AnalyticsService.get_popular_content(db=test_db)
        assert isinstance(popular, list)
        if popular:
            assert "id" in popular[0]
            assert "title" in popular[0]
            assert "view_count" in popular[0]

    @pytest.mark.asyncio
    async def test_get_session_analytics(self, test_db: AsyncSession):
        """Test getting session analytics."""
        result = await AnalyticsService.get_session_analytics(db=test_db)
        assert "active_sessions" in result
        assert "total_sessions" in result
        assert "device_breakdown" in result
        assert "browser_breakdown" in result


class TestAnalyticsRoutes:
    """Tests for analytics API endpoints."""

    def test_view_tracking_route_registered(self):
        """Test POST /content/{id}/views route is registered in the router."""
        from app.routes.content import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/{content_id}/views" in post_routes

    def test_popular_content_endpoint_requires_auth(self, client: TestClient):
        """Test GET /analytics/content/popular requires authentication."""
        response = client.get("/api/v1/analytics/content/popular")
        assert response.status_code in (307, 401, 403)

    def test_popular_content_route_registered(self):
        """Test GET /analytics/content/popular route is registered."""
        from app.routes.analytics import router

        get_routes = [r.path for r in router.routes if hasattr(r, "methods") and "GET" in r.methods]
        assert "/analytics/content/popular" in get_routes

    def test_session_analytics_endpoint_requires_auth(self, client: TestClient):
        """Test GET /analytics/sessions requires authentication."""
        response = client.get("/api/v1/analytics/sessions")
        assert response.status_code in (307, 401, 403)

    def test_session_analytics_route_registered(self):
        """Test GET /analytics/sessions route is registered."""
        from app.routes.analytics import router

        get_routes = [r.path for r in router.routes if hasattr(r, "methods") and "GET" in r.methods]
        assert "/analytics/sessions" in get_routes


class TestDashboardFixes:
    """Tests to verify dashboard service bug fixes."""

    def test_dashboard_service_uses_timestamp(self):
        """Verify dashboard_service uses ActivityLog.timestamp, not created_at."""
        import inspect

        from app.services import dashboard_service

        source = inspect.getsource(dashboard_service)
        assert "ActivityLog.created_at" not in source
        assert "ActivityLog.timestamp" in source

    def test_user_activity_timeline_no_resource_type(self):
        """Verify get_user_activity_timeline doesn't reference non-existent columns."""
        import inspect

        from app.services import dashboard_service

        source = inspect.getsource(dashboard_service.get_user_activity_timeline)
        assert "resource_type" not in source
        assert "resource_id" not in source


class TestMetricsSummary:
    """Tests for /metrics/summary endpoint."""

    def test_metrics_summary_endpoint(self, client: TestClient):
        """Test GET /metrics/summary returns JSON metrics."""
        response = client.get("/metrics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "http" in data
        assert "database" in data
        assert "cache" in data

    def test_metrics_summary_structure(self, client: TestClient):
        """Test /metrics/summary response structure."""
        response = client.get("/metrics/summary")
        data = response.json()
        assert "total_requests" in data["http"]
        assert "error_rate_percent" in data["http"]
        assert "total_queries" in data["database"]
        assert "hit_rate_percent" in data["cache"]
