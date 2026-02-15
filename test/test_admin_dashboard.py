"""
Tests for Admin Dashboard Enhancement (Phase 3.3).
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestSiteSettings:
    """Tests for site settings endpoints."""

    def test_site_settings_route_get_registered(self):
        """Test GET /settings/site route is registered."""
        from app.routes.settings import router

        get_routes = [r.path for r in router.routes if hasattr(r, "methods") and "GET" in r.methods]
        assert "/settings/site" in get_routes

    def test_site_settings_route_put_registered(self):
        """Test PUT /settings/site route is registered."""
        from app.routes.settings import router

        put_routes = [r.path for r in router.routes if hasattr(r, "methods") and "PUT" in r.methods]
        assert "/settings/site" in put_routes

    def test_site_settings_logo_route_registered(self):
        """Test POST /settings/site/logo route is registered."""
        from app.routes.settings import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/settings/site/logo" in post_routes

    def test_site_settings_favicon_route_registered(self):
        """Test POST /settings/site/favicon route is registered."""
        from app.routes.settings import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/settings/site/favicon" in post_routes

    def test_default_settings_structure(self):
        """Test default settings contain expected keys."""
        from app.routes.settings import DEFAULT_SETTINGS

        expected_keys = [
            "site_name",
            "site_description",
            "site_url",
            "timezone",
            "language",
            "posts_per_page",
            "allow_registration",
            "allow_comments",
            "maintenance_mode",
        ]
        for key in expected_keys:
            assert key in DEFAULT_SETTINGS

    def test_load_settings_returns_defaults(self, tmp_path, monkeypatch):
        """Test _load_settings returns defaults when no file exists."""
        from app.routes import settings as settings_module

        monkeypatch.setattr(settings_module, "SETTINGS_FILE", tmp_path / "nonexistent.json")
        result = settings_module._load_settings()
        assert result["site_name"] == "CMS Project"
        assert result["timezone"] == "UTC"

    def test_save_and_load_settings(self, tmp_path, monkeypatch):
        """Test saving and loading settings round-trip."""
        from app.routes import settings as settings_module

        settings_file = tmp_path / "site_settings.json"
        monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_file)
        monkeypatch.setattr(settings_module, "SETTINGS_DIR", tmp_path)

        test_settings = {"site_name": "Test Site", "language": "fr"}
        settings_module._save_settings(test_settings)

        loaded = json.loads(settings_file.read_text(encoding="utf-8"))
        assert loaded["site_name"] == "Test Site"
        assert loaded["language"] == "fr"

    def test_settings_get_requires_auth(self, client: TestClient):
        """Test GET /settings/site requires authentication."""
        response = client.get("/api/v1/settings/site")
        assert response.status_code in (307, 401, 403)


class TestBulkPathFixes:
    """Tests for bulk operation route path fixes."""

    def test_bulk_publish_path(self):
        """Test bulk publish route uses /content/bulk/publish path."""
        from app.routes.bulk import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/content/bulk/publish" in post_routes
        assert "/content/publish" not in post_routes

    def test_bulk_delete_path(self):
        """Test bulk delete route uses /content/bulk/delete path."""
        from app.routes.bulk import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/content/bulk/delete" in post_routes

    def test_bulk_update_status_path(self):
        """Test bulk update-status route uses /content/bulk/update-status path."""
        from app.routes.bulk import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/content/bulk/update-status" in post_routes

    def test_bulk_assign_tags_path(self):
        """Test bulk assign-tags route uses /content/bulk/assign-tags path."""
        from app.routes.bulk import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/content/bulk/assign-tags" in post_routes

    def test_bulk_update_category_path(self):
        """Test bulk update-category route uses /content/bulk/update-category path."""
        from app.routes.bulk import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/content/bulk/update-category" in post_routes

    def test_bulk_update_roles_path(self):
        """Test bulk update-roles route uses /users/bulk/update-roles path."""
        from app.routes.bulk import router

        post_routes = [r.path for r in router.routes if hasattr(r, "methods") and "POST" in r.methods]
        assert "/users/bulk/update-roles" in post_routes


class TestWebSocketBroadcasts:
    """Tests for WebSocket broadcast integration."""

    def test_content_routes_import_broadcast(self):
        """Verify content routes import broadcast_content_event."""
        import inspect

        from app.routes import content

        source = inspect.getsource(content)
        assert "broadcast_content_event" in source

    def test_comment_routes_import_broadcast(self):
        """Verify comment routes import broadcast_comment_event."""
        import inspect

        from app.routes import comments

        source = inspect.getsource(comments)
        assert "broadcast_comment_event" in source

    def test_websocket_manager_has_broadcast_helpers(self):
        """Verify websocket_manager exports broadcast helper functions."""
        from app.services.websocket_manager import (
            broadcast_comment_event,
            broadcast_content_event,
            send_notification_to_user,
        )

        assert callable(broadcast_content_event)
        assert callable(broadcast_comment_event)
        assert callable(send_notification_to_user)


class TestSettingsRegistration:
    """Tests for settings router registration in main app."""

    def test_settings_router_registered(self):
        """Test settings router is included in the app."""
        from main import app

        routes = [r.path for r in app.routes if hasattr(r, "path")]
        # The settings routes should be accessible under /api/v1
        settings_paths = [r for r in routes if "/settings" in r]
        assert len(settings_paths) > 0
