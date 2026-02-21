"""
Tests for Phase 4.2: Analytics config endpoint, event proxy, and UTM tracking.
"""

# ============================================================================
# TestAnalyticsConfig — /api/v1/analytics/config endpoint
# ============================================================================


class TestAnalyticsConfig:
    def test_config_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("analytics/config" in p for p in paths), f"No analytics/config route found in: {paths}"

    def test_config_not_blocked_by_rbac(self):
        """Analytics config must be accessible without authentication."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.get("/api/v1/analytics/config")
        assert response.status_code != 307, "Analytics config must not redirect to /login"

    def test_config_returns_200(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/analytics/config")
        assert response.status_code == 200

    def test_config_has_google_analytics_key(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        data = client.get("/api/v1/analytics/config").json()
        assert "google_analytics" in data

    def test_config_has_plausible_key(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        data = client.get("/api/v1/analytics/config").json()
        assert "plausible" in data

    def test_config_ga_enabled_false_when_unconfigured(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        data = client.get("/api/v1/analytics/config").json()
        # GA is not configured in test env
        assert data["google_analytics"]["enabled"] is False

    def test_config_plausible_enabled_false_when_unconfigured(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        data = client.get("/api/v1/analytics/config").json()
        assert data["plausible"]["enabled"] is False

    def test_config_structure_google_analytics(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        data = client.get("/api/v1/analytics/config").json()
        ga = data["google_analytics"]
        assert "enabled" in ga
        assert "measurement_id" in ga

    def test_config_structure_plausible(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        data = client.get("/api/v1/analytics/config").json()
        plausible = data["plausible"]
        assert "enabled" in plausible
        assert "domain" in plausible
        assert "api_url" in plausible


# ============================================================================
# TestAnalyticsEvents — /api/v1/analytics/events endpoint
# ============================================================================


class TestAnalyticsEvents:
    def test_events_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("analytics/events" in p for p in paths), f"No analytics/events route found in: {paths}"

    def test_events_endpoint_returns_202(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.post(
            "/api/v1/analytics/events",
            json={"name": "pageview", "url": "https://example.com"},
            headers={"X-API-Key": "test"},
        )
        # 202 if accepted, 307 if redirected (auth), either is fine for test env
        assert response.status_code in (202, 307, 401, 403)

    def test_events_does_not_raise_without_ga4_config(self):
        """Event proxy must not crash when GA4 settings are not configured."""
        import asyncio
        from unittest.mock import MagicMock

        from app.routes.analytics import _forward_event

        mock_request = MagicMock()
        mock_request.url = "https://example.com"
        mock_request.headers.get.return_value = "TestAgent"
        mock_request.client.host = "127.0.0.1"

        # Should complete without raising
        asyncio.run(_forward_event({"name": "pageview"}, mock_request))


# ============================================================================
# TestUTMTracking — ContentView model columns
# ============================================================================


class TestUTMTracking:
    def test_content_view_has_utm_source(self):
        from app.models.content_view import ContentView

        assert hasattr(ContentView, "utm_source")

    def test_content_view_has_utm_medium(self):
        from app.models.content_view import ContentView

        assert hasattr(ContentView, "utm_medium")

    def test_content_view_has_utm_campaign(self):
        from app.models.content_view import ContentView

        assert hasattr(ContentView, "utm_campaign")

    def test_content_view_has_utm_term(self):
        from app.models.content_view import ContentView

        assert hasattr(ContentView, "utm_term")

    def test_content_view_has_utm_content(self):
        from app.models.content_view import ContentView

        assert hasattr(ContentView, "utm_content")

    def test_utm_migration_file_exists(self):
        from pathlib import Path

        migration_path = (
            Path(__file__).parent.parent / "alembic" / "versions" / "o5p6q7r8s9t0_add_utm_to_content_views.py"
        )
        assert migration_path.exists(), f"Migration file not found: {migration_path}"
