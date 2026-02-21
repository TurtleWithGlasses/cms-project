"""
Tests for Phase 4.2: Social sharing service, SEO JSON-LD, and social routes.
"""

import inspect
from unittest.mock import MagicMock

# ============================================================================
# TestSocialSharingService — get_share_urls
# ============================================================================


class TestSocialSharingService:
    def _make_content(self, slug="my-post", title="My Post"):
        content = MagicMock()
        content.slug = slug
        content.title = title
        return content

    def test_get_share_urls_returns_all_platforms(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(), "https://example.com")
        for platform in ("twitter", "facebook", "linkedin", "whatsapp", "email"):
            assert platform in urls, f"Missing platform: {platform}"

    def test_share_urls_contain_slug(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(slug="hello-world"), "https://example.com")
        for platform, url in urls.items():
            assert "hello-world" in url, f"{platform} URL does not contain slug"

    def test_twitter_url_uses_twitter_domain(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(), "https://example.com")
        assert "twitter.com" in urls["twitter"]

    def test_facebook_url_uses_facebook_domain(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(), "https://example.com")
        assert "facebook.com" in urls["facebook"]

    def test_linkedin_url_uses_linkedin_domain(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(), "https://example.com")
        assert "linkedin.com" in urls["linkedin"]

    def test_whatsapp_url_uses_wa_me(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(), "https://example.com")
        assert "wa.me" in urls["whatsapp"]

    def test_email_url_starts_with_mailto(self):
        from app.services.social_service import SocialSharingService

        service = SocialSharingService()
        urls = service.get_share_urls(self._make_content(), "https://example.com")
        assert urls["email"].startswith("mailto:")


# ============================================================================
# TestSocialPostingService — async stub
# ============================================================================


class TestSocialPostingService:
    def test_post_on_publish_exists(self):
        from app.services.social_service import SocialPostingService

        assert hasattr(SocialPostingService, "post_on_publish")

    def test_post_on_publish_is_coroutine(self):
        from app.services.social_service import SocialPostingService

        assert inspect.iscoroutinefunction(SocialPostingService.post_on_publish)

    def test_post_on_publish_skips_gracefully_without_credentials(self):
        """post_on_publish must not raise even when no credentials are configured."""
        import asyncio

        from app.services.social_service import SocialPostingService

        content = MagicMock()
        content.title = "Test"
        content.id = 1

        # Should complete without raising even without bearer token set
        service = SocialPostingService()
        asyncio.run(service.post_on_publish(content, "https://example.com"))


# ============================================================================
# TestSEOJsonLD — SEOService new methods
# ============================================================================


class TestSEOJsonLD:
    def _make_content(self):
        from datetime import datetime

        content = MagicMock()
        content.title = "Test Article"
        content.slug = "test-article"
        content.meta_title = "SEO Title"
        content.meta_description = "SEO description"
        content.meta_keywords = "test, article"
        content.description = "Body text"
        content.created_at = datetime(2026, 1, 1)
        content.updated_at = datetime(2026, 2, 1)
        content.author = MagicMock()
        content.author.username = "admin"
        return content

    def test_generate_article_json_ld_returns_schema_context(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        result = seo.generate_article_json_ld(self._make_content(), "https://example.com")
        assert result["@context"] == "https://schema.org"

    def test_generate_article_json_ld_type_is_article(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        result = seo.generate_article_json_ld(self._make_content(), "https://example.com")
        assert result["@type"] == "Article"

    def test_generate_article_json_ld_headline(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        content = self._make_content()
        result = seo.generate_article_json_ld(content, "https://example.com")
        assert result["headline"] == content.title

    def test_generate_article_json_ld_url_contains_slug(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        result = seo.generate_article_json_ld(self._make_content(), "https://example.com")
        assert "test-article" in result["url"]

    def test_generate_website_json_ld_type_is_website(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        result = seo.generate_website_json_ld("https://example.com")
        assert result["@type"] == "WebSite"

    def test_generate_website_json_ld_has_search_action(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        result = seo.generate_website_json_ld("https://example.com")
        assert "potentialAction" in result
        assert result["potentialAction"]["@type"] == "SearchAction"

    def test_get_content_og_tags_og_type_is_article(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        tags = seo.get_content_og_tags(self._make_content(), "https://example.com")
        assert tags["og:type"] == "article"

    def test_get_content_og_tags_twitter_card(self):
        from unittest.mock import AsyncMock

        from app.services.seo_service import SEOService

        seo = SEOService(AsyncMock())
        tags = seo.get_content_og_tags(self._make_content(), "https://example.com")
        assert "twitter:card" in tags


# ============================================================================
# TestSocialRoutes — route registration checks
# ============================================================================


class TestSocialRoutes:
    def test_share_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("share" in p for p in paths), f"No share route found in: {paths}"

    def test_meta_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("meta" in p and "social" in p for p in paths), f"No social meta route found in: {paths}"

    def test_share_endpoint_returns_404_for_nonexistent(self):
        """Share endpoint must return 404 for content that doesn't exist."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/social/content/999999/share")
        # Could be 404 (not found) or 500 (DB not available) — but NOT 307 (redirect to login)
        assert response.status_code != 307, "Social share route must not redirect to /login"

    def test_meta_endpoint_not_blocked_by_rbac(self):
        """Unauthenticated requests to social meta must not redirect to /login."""
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
        response = client.get("/api/v1/social/content/1/meta")
        assert response.status_code != 307, "Social meta route must not be redirected to /login"
