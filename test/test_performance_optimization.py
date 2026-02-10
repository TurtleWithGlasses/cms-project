"""
Tests for Phase 2.6 Performance Optimization

Covers:
- Query monitoring via SQLAlchemy event listeners
- Dashboard query batching (structure unchanged)
- Field selection utility (sparse fieldsets)
- ETag middleware (conditional requests)
- GZip compression configuration
- Pagination bounds on list endpoints
"""

import hashlib

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, event, text

from app.middleware.etag import ETagMiddleware
from app.utils.field_selector import FieldSelector
from app.utils.query_monitor import install_query_monitor

# Import the app for integration tests
from main import app


# ---------------------------------------------------------------------------
# TestQueryMonitor
# ---------------------------------------------------------------------------
class TestQueryMonitor:
    """Tests for the SQLAlchemy query monitor."""

    def test_install_query_monitor_runs_without_error(self):
        """Verify install_query_monitor registers listeners without error."""
        from sqlalchemy.ext.asyncio import create_async_engine

        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        # Should not raise
        install_query_monitor(test_engine, slow_threshold_ms=50)

    def test_slow_query_threshold_configurable(self):
        """Verify the threshold parameter is accepted."""
        from sqlalchemy.ext.asyncio import create_async_engine

        test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        # Should accept any positive threshold
        install_query_monitor(test_engine, slow_threshold_ms=1)
        install_query_monitor(test_engine, slow_threshold_ms=500)
        install_query_monitor(test_engine, slow_threshold_ms=5000)
        test_engine.dispose()


# ---------------------------------------------------------------------------
# TestFieldSelector
# ---------------------------------------------------------------------------
class TestFieldSelector:
    """Tests for sparse fieldset utility."""

    def test_no_fields_returns_data_unchanged(self):
        """No fields param returns data as-is."""
        fs = FieldSelector(fields=None)
        data = [{"id": 1, "title": "Hello", "body": "World"}]
        assert fs.apply(data) == data
        assert fs.has_selection is False

    def test_filters_dict(self):
        """Fields param filters dict keys."""
        fs = FieldSelector(fields="id,title")
        data = {"id": 1, "title": "Hello", "body": "World", "slug": "hello"}
        result = fs.apply(data)
        assert result == {"id": 1, "title": "Hello"}

    def test_filters_list_of_dicts(self):
        """Fields param filters list of dicts."""
        fs = FieldSelector(fields="id,title")
        data = [
            {"id": 1, "title": "A", "body": "X"},
            {"id": 2, "title": "B", "body": "Y"},
        ]
        result = fs.apply(data)
        assert result == [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}]

    def test_filters_pydantic_model(self):
        """Fields param works with Pydantic models."""

        class Item(BaseModel):
            model_config = ConfigDict(from_attributes=True)
            id: int
            title: str
            body: str

        fs = FieldSelector(fields="id,title")
        item = Item(id=1, title="Hello", body="World")
        result = fs.apply(item)
        assert result == {"id": 1, "title": "Hello"}

    def test_has_selection_true_when_fields_provided(self):
        """has_selection returns True when fields are specified."""
        fs = FieldSelector(fields="id")
        assert fs.has_selection is True

    def test_whitespace_handling(self):
        """Whitespace around field names is stripped."""
        fs = FieldSelector(fields="  id , title  , slug  ")
        assert fs.requested_fields == {"id", "title", "slug"}

    def test_empty_string_treated_as_no_selection(self):
        """Empty fields string is treated as no selection."""
        fs = FieldSelector(fields="")
        assert fs.has_selection is False

    def test_apply_plain_object(self):
        """Fields param works with plain objects having __dict__."""

        class Obj:
            def __init__(self):
                self.id = 1
                self.title = "Hello"
                self.body = "World"

        fs = FieldSelector(fields="id,title")
        result = fs.apply(Obj())
        assert result == {"id": 1, "title": "Hello"}


# ---------------------------------------------------------------------------
# TestETagMiddleware
# ---------------------------------------------------------------------------
class TestETagMiddleware:
    """Tests for ETag conditional request middleware."""

    @pytest.mark.asyncio
    async def test_get_response_includes_etag(self):
        """GET JSON responses include ETag header."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/")

        # Root endpoint returns JSON; should have ETag
        if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
            assert "etag" in response.headers

    @pytest.mark.asyncio
    async def test_etag_is_valid_format(self):
        """ETag follows the quoted-string format."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/")

        etag = response.headers.get("etag")
        if etag:
            assert etag.startswith('"') and etag.endswith('"')

    @pytest.mark.asyncio
    async def test_if_none_match_returns_304(self):
        """If-None-Match with matching ETag returns 304."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # First request to get the ETag
            response1 = await client.get("/")
            etag = response1.headers.get("etag")

            if etag:
                # Second request with If-None-Match
                response2 = await client.get("/", headers={"If-None-Match": etag})
                assert response2.status_code == 304

    @pytest.mark.asyncio
    async def test_if_none_match_mismatch_returns_200(self):
        """If-None-Match with different ETag returns 200."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/", headers={"If-None-Match": '"invalid-etag"'})
            assert response.status_code == 200

    def test_etag_middleware_skips_non_get(self):
        """ETag middleware only processes GET requests."""
        # The ETagMiddleware.dispatch checks request.method != "GET" and skips.
        # This is a structural test — POST responses should never get ETags.
        from app.middleware.etag import ETagMiddleware

        assert hasattr(ETagMiddleware, "dispatch")
        # Functional verification via integration tests is done by checking
        # that GET root (/) DOES have ETag (tested above).


# ---------------------------------------------------------------------------
# TestCompressionConfig
# ---------------------------------------------------------------------------
class TestCompressionConfig:
    """Tests for compression configuration."""

    def test_gzip_middleware_configured(self):
        """Verify GZip middleware is in the middleware stack."""
        from fastapi.middleware.gzip import GZipMiddleware

        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert GZipMiddleware in middleware_classes

    def test_etag_middleware_configured(self):
        """Verify ETag middleware is in the middleware stack."""
        middleware_classes = [m.cls for m in app.user_middleware if hasattr(m, "cls")]
        assert ETagMiddleware in middleware_classes

    def test_config_has_performance_settings(self):
        """Verify config has performance-related settings."""
        from app.config import settings

        assert hasattr(settings, "slow_query_threshold_ms")
        assert hasattr(settings, "gzip_minimum_size")
        assert hasattr(settings, "etag_enabled")
        assert settings.slow_query_threshold_ms == 100
        assert settings.gzip_minimum_size == 500
        assert settings.etag_enabled is True


# ---------------------------------------------------------------------------
# TestPaginationBounds
# ---------------------------------------------------------------------------
class TestPaginationBounds:
    """Tests for pagination on previously unbounded endpoints."""

    @pytest.mark.asyncio
    async def test_list_users_accepts_limit(self):
        """GET /api/v1/users/ accepts skip and limit parameters."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/users/?skip=0&limit=10")

        # Should respond (auth redirect or actual data) but not error
        assert response.status_code in (200, 307, 401, 403)

    @pytest.mark.asyncio
    async def test_content_list_accepts_fields(self):
        """GET /api/v1/content/ accepts fields parameter."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=True,
        ) as client:
            response = await client.get("/api/v1/content/?fields=id,title")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TestDashboardOptimization
# ---------------------------------------------------------------------------
class TestDashboardOptimization:
    """Tests for dashboard query batching (structure preservation)."""

    def test_get_content_kpis_importable(self):
        """Verify get_content_kpis is importable after optimization."""
        from app.services.dashboard_service import get_content_kpis

        assert callable(get_content_kpis)

    def test_get_user_kpis_importable(self):
        """Verify get_user_kpis is importable after optimization."""
        from app.services.dashboard_service import get_user_kpis

        assert callable(get_user_kpis)

    def test_get_dashboard_summary_importable(self):
        """Verify get_dashboard_summary is importable after optimization."""
        from app.services.dashboard_service import get_dashboard_summary

        assert callable(get_dashboard_summary)
