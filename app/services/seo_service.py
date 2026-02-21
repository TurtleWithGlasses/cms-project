"""
SEO Service

Provides sitemap.xml and RSS feed generation for search engine optimization.
"""

import logging
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring  # nosec B405

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.category import Category
from app.models.content import Content, ContentStatus

logger = logging.getLogger(__name__)


class SEOService:
    """Service for generating SEO-related content."""

    def __init__(self, db: AsyncSession, base_url: str | None = None):
        self.db = db
        self.base_url = base_url or getattr(settings, "base_url", "http://localhost:8000")

    async def generate_sitemap(self) -> str:
        """
        Generate XML sitemap for all published content.

        Returns:
            XML string in sitemap format
        """
        # Create root element
        urlset = Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        urlset.set("xmlns:news", "http://www.google.com/schemas/sitemap-news/0.9")

        # Add homepage
        self._add_url(urlset, "/", priority="1.0", changefreq="daily")

        # Add static pages
        static_pages = [
            ("/about", "0.8", "monthly"),
            ("/contact", "0.6", "monthly"),
        ]
        for path, priority, freq in static_pages:
            self._add_url(urlset, path, priority=priority, changefreq=freq)

        # Add published content
        result = await self.db.execute(
            select(Content).where(Content.status == ContentStatus.PUBLISHED).order_by(Content.updated_at.desc())
        )
        contents = result.scalars().all()

        for content in contents:
            lastmod = content.updated_at.strftime("%Y-%m-%d") if content.updated_at else None
            self._add_url(
                urlset,
                f"/content/{content.slug}",
                lastmod=lastmod,
                priority="0.7",
                changefreq="weekly",
            )

        # Add categories
        result = await self.db.execute(select(Category))
        categories = result.scalars().all()

        for category in categories:
            self._add_url(
                urlset,
                f"/category/{category.slug}",
                priority="0.6",
                changefreq="weekly",
            )

        # Generate XML string
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content = tostring(urlset, encoding="unicode")

        logger.info(f"Generated sitemap with {len(contents)} content items")
        return xml_declaration + xml_content

    async def generate_sitemap_index(self, sitemap_urls: list[str]) -> str:
        """
        Generate sitemap index for large sites with multiple sitemaps.

        Args:
            sitemap_urls: List of individual sitemap URLs

        Returns:
            XML string in sitemap index format
        """
        sitemapindex = Element("sitemapindex")
        sitemapindex.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

        for url in sitemap_urls:
            sitemap = SubElement(sitemapindex, "sitemap")
            loc = SubElement(sitemap, "loc")
            loc.text = f"{self.base_url}{url}"
            lastmod = SubElement(sitemap, "lastmod")
            lastmod.text = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content = tostring(sitemapindex, encoding="unicode")

        return xml_declaration + xml_content

    async def generate_rss_feed(
        self,
        limit: int = 20,
        category_id: int | None = None,
    ) -> str:
        """
        Generate RSS 2.0 feed for published content.

        Args:
            limit: Maximum number of items in feed
            category_id: Optional category filter

        Returns:
            XML string in RSS 2.0 format
        """
        # Create RSS structure
        rss = Element("rss")
        rss.set("version", "2.0")
        rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
        rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")

        channel = SubElement(rss, "channel")

        # Channel metadata
        title = SubElement(channel, "title")
        title.text = getattr(settings, "app_name", "CMS")

        link = SubElement(channel, "link")
        link.text = self.base_url

        description = SubElement(channel, "description")
        description.text = getattr(settings, "app_description", "Content Management System")

        language = SubElement(channel, "language")
        language.text = "en-us"

        # Last build date
        last_build_date = SubElement(channel, "lastBuildDate")
        last_build_date.text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Atom self link
        atom_link = SubElement(channel, "{http://www.w3.org/2005/Atom}link")
        atom_link.set("href", f"{self.base_url}/feed.xml")
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")

        # Build query
        query = select(Content).where(Content.status == ContentStatus.PUBLISHED)

        if category_id:
            query = query.where(Content.category_id == category_id)

        query = query.order_by(Content.publish_date.desc()).limit(limit)

        result = await self.db.execute(query)
        contents = result.scalars().all()

        # Add items
        for content in contents:
            item = SubElement(channel, "item")

            item_title = SubElement(item, "title")
            item_title.text = content.title

            item_link = SubElement(item, "link")
            item_link.text = f"{self.base_url}/content/{content.slug}"

            item_guid = SubElement(item, "guid")
            item_guid.set("isPermaLink", "true")
            item_guid.text = f"{self.base_url}/content/{content.slug}"

            if content.description:
                item_description = SubElement(item, "description")
                item_description.text = content.description

            if content.body:
                content_encoded = SubElement(item, "{http://purl.org/rss/1.0/modules/content/}encoded")
                content_encoded.text = content.body[:500] + "..." if len(content.body) > 500 else content.body

            pub_date = content.publish_date or content.created_at
            if pub_date:
                item_pub_date = SubElement(item, "pubDate")
                item_pub_date.text = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")

            if content.author:
                item_author = SubElement(item, "author")
                item_author.text = content.author.email

            if content.category:
                item_category = SubElement(item, "category")
                item_category.text = content.category.name

        # Generate XML string
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content = tostring(rss, encoding="unicode")

        logger.info(f"Generated RSS feed with {len(contents)} items")
        return xml_declaration + xml_content

    async def generate_atom_feed(
        self,
        limit: int = 20,
        category_id: int | None = None,
    ) -> str:
        """
        Generate Atom feed for published content.

        Args:
            limit: Maximum number of items in feed
            category_id: Optional category filter

        Returns:
            XML string in Atom format
        """
        # Create Atom structure
        feed = Element("feed")
        feed.set("xmlns", "http://www.w3.org/2005/Atom")

        # Feed metadata
        title = SubElement(feed, "title")
        title.text = getattr(settings, "app_name", "CMS")

        subtitle = SubElement(feed, "subtitle")
        subtitle.text = getattr(settings, "app_description", "Content Management System")

        link_self = SubElement(feed, "link")
        link_self.set("href", f"{self.base_url}/atom.xml")
        link_self.set("rel", "self")
        link_self.set("type", "application/atom+xml")

        link_alt = SubElement(feed, "link")
        link_alt.set("href", self.base_url)
        link_alt.set("rel", "alternate")
        link_alt.set("type", "text/html")

        feed_id = SubElement(feed, "id")
        feed_id.text = self.base_url

        updated = SubElement(feed, "updated")
        updated.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build query
        query = select(Content).where(Content.status == ContentStatus.PUBLISHED)

        if category_id:
            query = query.where(Content.category_id == category_id)

        query = query.order_by(Content.publish_date.desc()).limit(limit)

        result = await self.db.execute(query)
        contents = result.scalars().all()

        # Add entries
        for content in contents:
            entry = SubElement(feed, "entry")

            entry_title = SubElement(entry, "title")
            entry_title.text = content.title

            entry_link = SubElement(entry, "link")
            entry_link.set("href", f"{self.base_url}/content/{content.slug}")
            entry_link.set("rel", "alternate")
            entry_link.set("type", "text/html")

            entry_id = SubElement(entry, "id")
            entry_id.text = f"{self.base_url}/content/{content.slug}"

            entry_updated = SubElement(entry, "updated")
            update_date = content.updated_at or content.created_at
            entry_updated.text = update_date.strftime("%Y-%m-%dT%H:%M:%SZ") if update_date else ""

            if content.publish_date:
                entry_published = SubElement(entry, "published")
                entry_published.text = content.publish_date.strftime("%Y-%m-%dT%H:%M:%SZ")

            if content.author:
                author = SubElement(entry, "author")
                author_name = SubElement(author, "name")
                author_name.text = content.author.username or content.author.email

            if content.description:
                summary = SubElement(entry, "summary")
                summary.set("type", "text")
                summary.text = content.description

            if content.body:
                entry_content = SubElement(entry, "content")
                entry_content.set("type", "html")
                entry_content.text = content.body[:1000] if len(content.body) > 1000 else content.body

            if content.category:
                category_elem = SubElement(entry, "category")
                category_elem.set("term", content.category.slug)
                category_elem.set("label", content.category.name)

        # Generate XML string
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content = tostring(feed, encoding="unicode")

        logger.info(f"Generated Atom feed with {len(contents)} items")
        return xml_declaration + xml_content

    async def generate_robots_txt(self) -> str:
        """
        Generate robots.txt content.

        Returns:
            robots.txt content string
        """
        lines = [
            "User-agent: *",
            "Allow: /",
            "",
            "# Disallow admin and API paths",
            "Disallow: /admin/",
            "Disallow: /api/",
            "Disallow: /auth/",
            "",
            "# Sitemap",
            f"Sitemap: {self.base_url}/sitemap.xml",
            "",
            "# Crawl-delay for polite bots",
            "Crawl-delay: 1",
        ]
        return "\n".join(lines)

    def generate_article_json_ld(self, content: object, base_url: str) -> dict:
        """Schema.org Article JSON-LD for a published content item."""
        return {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": content.title,
            "description": content.meta_description or getattr(content, "description", "") or "",
            "url": f"{base_url}/content/{content.slug}",
            "datePublished": content.created_at.isoformat() if content.created_at else None,
            "dateModified": content.updated_at.isoformat() if content.updated_at else None,
            "author": {
                "@type": "Person",
                "name": content.author.username if content.author else "Unknown",
            },
            "publisher": {
                "@type": "Organization",
                "name": settings.app_name,
                "url": base_url,
            },
            "keywords": content.meta_keywords or "",
        }

    def generate_website_json_ld(self, base_url: str) -> dict:
        """Schema.org WebSite JSON-LD with SearchAction."""
        return {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": settings.app_name,
            "url": base_url,
            "potentialAction": {
                "@type": "SearchAction",
                "target": f"{base_url}/api/v1/search/?q={{search_term_string}}",
                "query-input": "required name=search_term_string",
            },
        }

    def get_content_og_tags(self, content: object, base_url: str) -> dict[str, str]:
        """Open Graph + Twitter Card meta tag dict for a content item."""
        url = f"{base_url}/content/{content.slug}"
        title = content.meta_title or content.title
        description = content.meta_description or getattr(content, "description", "") or ""
        tags: dict[str, str] = {
            "og:type": "article",
            "og:url": url,
            "og:title": title,
            "og:description": description,
            "og:site_name": settings.app_name,
            # Twitter Card
            "twitter:card": "summary_large_image",
            "twitter:url": url,
            "twitter:title": title,
            "twitter:description": description,
        }
        if settings.twitter_handle:
            tags["twitter:site"] = settings.twitter_handle
        if settings.facebook_app_id:
            tags["fb:app_id"] = settings.facebook_app_id
        return tags

    def _add_url(
        self,
        parent: Element,
        path: str,
        lastmod: str | None = None,
        changefreq: str = "weekly",
        priority: str = "0.5",
    ) -> None:
        """Add a URL entry to the sitemap."""
        url = SubElement(parent, "url")

        loc = SubElement(url, "loc")
        loc.text = f"{self.base_url}{path}"

        if lastmod:
            lastmod_elem = SubElement(url, "lastmod")
            lastmod_elem.text = lastmod

        changefreq_elem = SubElement(url, "changefreq")
        changefreq_elem.text = changefreq

        priority_elem = SubElement(url, "priority")
        priority_elem.text = priority


# Dependency for FastAPI
async def get_seo_service(db: AsyncSession, base_url: str | None = None) -> SEOService:
    """FastAPI dependency for SEOService."""
    return SEOService(db, base_url)
