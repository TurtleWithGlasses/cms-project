"""
Tests for SEO functionality (sitemap, RSS, robots.txt).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.user import User
from app.services.seo_service import SEOService


@pytest.fixture
async def test_category(test_db: AsyncSession) -> Category:
    """Create a test category."""
    category = Category(
        name="Technology",
        slug="technology",
        description="Tech articles",
    )
    test_db.add(category)
    await test_db.commit()
    await test_db.refresh(category)
    return category


@pytest.fixture
async def test_published_content(test_db: AsyncSession, test_user: User, test_category: Category) -> list[Content]:
    """Create multiple published content items."""
    contents = []
    for i in range(3):
        content = Content(
            title=f"Test Article {i}",
            body=f"This is the body of article {i}.",
            description=f"Description for article {i}",
            slug=f"test-article-{i}",
            status=ContentStatus.PUBLISHED,
            author_id=test_user.id,
            category_id=test_category.id,
        )
        test_db.add(content)
        contents.append(content)

    await test_db.commit()
    for content in contents:
        await test_db.refresh(content)

    return contents


class TestSEOService:
    """Tests for SEOService."""

    @pytest.mark.asyncio
    async def test_generate_sitemap(self, test_db: AsyncSession, test_published_content: list[Content]):
        """Test generating XML sitemap."""
        service = SEOService(test_db, base_url="https://example.com")
        sitemap = await service.generate_sitemap()

        # Check XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in sitemap
        assert "http://www.sitemaps.org/schemas/sitemap/0.9" in sitemap
        assert "<urlset" in sitemap
        assert "</urlset>" in sitemap

        # Check content URLs are included
        for content in test_published_content:
            assert f"/content/{content.slug}" in sitemap

        # Check homepage
        assert "https://example.com/" in sitemap

    @pytest.mark.asyncio
    async def test_generate_sitemap_empty(self, test_db: AsyncSession):
        """Test generating sitemap with no content."""
        service = SEOService(test_db, base_url="https://example.com")
        sitemap = await service.generate_sitemap()

        assert '<?xml version="1.0" encoding="UTF-8"?>' in sitemap
        assert "<urlset" in sitemap

    @pytest.mark.asyncio
    async def test_generate_rss_feed(self, test_db: AsyncSession, test_published_content: list[Content]):
        """Test generating RSS 2.0 feed."""
        service = SEOService(test_db, base_url="https://example.com")
        rss = await service.generate_rss_feed(limit=10)

        # Check RSS structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in rss
        assert "<rss" in rss
        assert 'version="2.0"' in rss
        assert "<channel>" in rss
        assert "</channel>" in rss

        # Check items
        assert "<item>" in rss
        for content in test_published_content:
            assert content.title in rss

    @pytest.mark.asyncio
    async def test_generate_rss_feed_with_limit(self, test_db: AsyncSession, test_published_content: list[Content]):
        """Test RSS feed respects limit."""
        service = SEOService(test_db, base_url="https://example.com")
        rss = await service.generate_rss_feed(limit=1)

        # Should only have 1 item
        assert rss.count("<item>") == 1

    @pytest.mark.asyncio
    async def test_generate_rss_feed_by_category(
        self, test_db: AsyncSession, test_published_content: list[Content], test_category: Category
    ):
        """Test RSS feed filtered by category."""
        service = SEOService(test_db, base_url="https://example.com")
        rss = await service.generate_rss_feed(category_id=test_category.id)

        # All test content is in the category
        assert rss.count("<item>") == len(test_published_content)

    @pytest.mark.asyncio
    async def test_generate_atom_feed(self, test_db: AsyncSession, test_published_content: list[Content]):
        """Test generating Atom feed."""
        service = SEOService(test_db, base_url="https://example.com")
        atom = await service.generate_atom_feed(limit=10)

        # Check Atom structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in atom
        assert "<feed" in atom
        assert "http://www.w3.org/2005/Atom" in atom
        assert "<entry>" in atom

        # Check entries
        for content in test_published_content:
            assert content.title in atom

    @pytest.mark.asyncio
    async def test_generate_robots_txt(self, test_db: AsyncSession):
        """Test generating robots.txt."""
        service = SEOService(test_db, base_url="https://example.com")
        robots = await service.generate_robots_txt()

        assert "User-agent: *" in robots
        assert "Allow: /" in robots
        assert "Disallow: /admin/" in robots
        assert "Disallow: /api/" in robots
        assert "Sitemap: https://example.com/sitemap.xml" in robots

    @pytest.mark.asyncio
    async def test_generate_sitemap_index(self, test_db: AsyncSession):
        """Test generating sitemap index."""
        service = SEOService(test_db, base_url="https://example.com")
        sitemap_urls = ["/sitemap-content.xml", "/sitemap-pages.xml"]
        index = await service.generate_sitemap_index(sitemap_urls)

        assert '<?xml version="1.0" encoding="UTF-8"?>' in index
        assert "<sitemapindex" in index
        assert "https://example.com/sitemap-content.xml" in index
        assert "https://example.com/sitemap-pages.xml" in index


class TestSEORoutes:
    """Tests for SEO API routes."""

    def test_get_sitemap(self, client, test_db, test_user, test_published_content):
        """Test getting sitemap via API."""
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"

        content = response.text
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert "<urlset" in content

    def test_get_robots_txt(self, client):
        """Test getting robots.txt via API."""
        response = client.get("/robots.txt")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        content = response.text
        assert "User-agent:" in content
        assert "Sitemap:" in content

    def test_get_rss_feed(self, client, test_db, test_user, test_published_content):
        """Test getting RSS feed via API."""
        response = client.get("/feed.xml")
        assert response.status_code == 200
        assert "application/rss+xml" in response.headers["content-type"]

        content = response.text
        assert "<rss" in content
        assert "<channel>" in content

    def test_get_rss_feed_with_limit(self, client):
        """Test RSS feed with limit parameter."""
        response = client.get("/feed.xml?limit=5")
        assert response.status_code == 200

    def test_get_atom_feed(self, client, test_db, test_user, test_published_content):
        """Test getting Atom feed via API."""
        response = client.get("/atom.xml")
        assert response.status_code == 200
        assert "application/atom+xml" in response.headers["content-type"]

        content = response.text
        assert "<feed" in content
        assert "http://www.w3.org/2005/Atom" in content

    def test_get_category_rss_feed(self, client, test_db, test_user, test_published_content, test_category):
        """Test getting category-specific RSS feed."""
        response = client.get(f"/feed/category/{test_category.id}")
        assert response.status_code == 200
        assert "application/rss+xml" in response.headers["content-type"]

    def test_sitemap_caching_headers(self, client):
        """Test that sitemap has caching headers."""
        response = client.get("/sitemap.xml")
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "max-age" in response.headers["Cache-Control"]

    def test_rss_caching_headers(self, client):
        """Test that RSS feed has caching headers."""
        response = client.get("/feed.xml")
        assert response.status_code == 200
        assert "Cache-Control" in response.headers
