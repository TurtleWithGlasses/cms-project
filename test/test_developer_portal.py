"""
Tests for Phase 4.4: API Documentation & Developer Portal.
"""

# ============================================================================
# TestDeveloperPortalRoute — GET /developer
# ============================================================================


class TestDeveloperPortalRoute:
    def test_developer_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/developer" in paths, f"/developer route missing: {paths}"

    def test_developer_portal_is_public(self):
        """GET /developer must return 200 without auth (no redirect to /login)."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/developer")
        assert response.status_code == 200

    def test_developer_portal_returns_html(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/developer")
        assert "text/html" in response.headers.get("content-type", "")

    def test_developer_portal_contains_app_name(self):
        from fastapi.testclient import TestClient

        from app.config import settings
        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/developer")
        assert settings.app_name in response.text

    def test_developer_portal_contains_swagger_link(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/developer")
        assert "/docs" in response.text

    def test_developer_portal_contains_redoc_link(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/developer")
        assert "/redoc" in response.text

    def test_developer_portal_not_in_rbac_redirect(self):
        """RBAC must include /developer in public_paths."""
        from app.middleware.rbac import RBACMiddleware

        middleware = RBACMiddleware(app=None)
        assert "/developer" in middleware.public_paths


# ============================================================================
# TestChangelogRoute — GET /api/v1/developer/changelog
# ============================================================================


class TestChangelogRoute:
    def test_changelog_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert "/api/v1/developer/changelog" in paths, f"/api/v1/developer/changelog route missing: {paths}"

    def test_changelog_is_public(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/developer/changelog")
        assert response.status_code == 200

    def test_changelog_returns_json(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/developer/changelog")
        assert "application/json" in response.headers.get("content-type", "")

    def test_changelog_has_app_field(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        data = client.get("/api/v1/developer/changelog").json()
        assert "app" in data

    def test_changelog_has_current_version(self):
        from fastapi.testclient import TestClient

        from app.config import settings
        from main import app

        client = TestClient(app, follow_redirects=False)
        data = client.get("/api/v1/developer/changelog").json()
        assert data.get("current_version") == settings.app_version

    def test_changelog_has_entries_list(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        data = client.get("/api/v1/developer/changelog").json()
        assert isinstance(data.get("changelog"), list)
        assert len(data["changelog"]) > 0

    def test_changelog_entries_have_required_fields(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        data = client.get("/api/v1/developer/changelog").json()
        for entry in data["changelog"]:
            assert "version" in entry
            assert "date" in entry
            assert "title" in entry
            assert "highlights" in entry
            assert isinstance(entry["highlights"], list)

    def test_changelog_not_in_rbac_redirect(self):
        """RBAC must include /api/v1/developer/changelog in public_paths."""
        from app.middleware.rbac import RBACMiddleware

        middleware = RBACMiddleware(app=None)
        assert "/api/v1/developer/changelog" in middleware.public_paths


# ============================================================================
# TestOpenAPISecuritySchemes — custom OpenAPI schema
# ============================================================================


class TestOpenAPISecuritySchemes:
    def _get_schema(self):
        from main import app

        return app.openapi()

    def test_openapi_schema_has_components(self):
        schema = self._get_schema()
        assert "components" in schema

    def test_openapi_schema_has_security_schemes(self):
        schema = self._get_schema()
        assert "securitySchemes" in schema["components"]

    def test_bearer_auth_scheme_exists(self):
        schema = self._get_schema()
        schemes = schema["components"]["securitySchemes"]
        assert "BearerAuth" in schemes

    def test_bearer_auth_is_http_bearer(self):
        schema = self._get_schema()
        bearer = schema["components"]["securitySchemes"]["BearerAuth"]
        assert bearer["type"] == "http"
        assert bearer["scheme"] == "bearer"
        assert bearer.get("bearerFormat") == "JWT"

    def test_api_key_auth_scheme_exists(self):
        schema = self._get_schema()
        schemes = schema["components"]["securitySchemes"]
        assert "APIKeyAuth" in schemes

    def test_api_key_auth_is_header_key(self):
        schema = self._get_schema()
        apikey = schema["components"]["securitySchemes"]["APIKeyAuth"]
        assert apikey["type"] == "apiKey"
        assert apikey["in"] == "header"
        assert apikey["name"] == "X-API-Key"


# ============================================================================
# TestOpenAPIMetadata — app title, version, description, tags
# ============================================================================


class TestOpenAPIMetadata:
    def test_app_title_matches_settings(self):
        from app.config import settings
        from main import app

        assert app.title == settings.app_name

    def test_app_version_matches_settings(self):
        from app.config import settings
        from main import app

        assert app.version == settings.app_version

    def test_app_has_description(self):
        from main import app

        assert app.description
        assert len(app.description) > 10

    def test_app_has_contact(self):
        from main import app

        assert app.contact is not None
        assert "name" in app.contact

    def test_app_has_license_info(self):
        from main import app

        assert app.license_info is not None
        assert "name" in app.license_info

    def test_openapi_tags_defined(self):
        from main import app

        assert app.openapi_tags is not None
        assert len(app.openapi_tags) > 0

    def test_developer_portal_tag_present(self):
        from main import app

        tag_names = [t["name"] for t in (app.openapi_tags or [])]
        assert "Developer Portal" in tag_names
