"""
Tests for Phase 4.3: Import/Export — XML, WordPress WXR, Markdown formats.
"""

import io
import zipfile

# ============================================================================
# TestXMLExportService — export_content_xml
# ============================================================================


class TestXMLExportService:
    def test_export_content_xml_method_exists(self):
        from app.services.export_service import ExportService

        assert hasattr(ExportService, "export_content_xml")

    def test_export_content_xml_is_coroutine(self):
        import inspect

        from app.services.export_service import ExportService

        assert inspect.iscoroutinefunction(ExportService.export_content_xml)

    def test_export_content_xml_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("content/xml" in p for p in paths), f"content/xml route missing: {paths}"

    def test_export_content_xml_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/content/xml")
        assert response.status_code in (307, 401, 403)


# ============================================================================
# TestWordPressExportService — export_content_wordpress
# ============================================================================


class TestWordPressExportService:
    def test_export_content_wordpress_method_exists(self):
        from app.services.export_service import ExportService

        assert hasattr(ExportService, "export_content_wordpress")

    def test_export_content_wordpress_is_coroutine(self):
        import inspect

        from app.services.export_service import ExportService

        assert inspect.iscoroutinefunction(ExportService.export_content_wordpress)

    def test_export_content_wordpress_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("content/wordpress" in p for p in paths), f"wordpress route missing: {paths}"

    def test_export_content_wordpress_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/content/wordpress")
        assert response.status_code in (307, 401, 403)


# ============================================================================
# TestMarkdownExportService — export_content_markdown_zip
# ============================================================================


class TestMarkdownExportService:
    def test_export_content_markdown_zip_method_exists(self):
        from app.services.export_service import ExportService

        assert hasattr(ExportService, "export_content_markdown_zip")

    def test_export_content_markdown_zip_is_coroutine(self):
        import inspect

        from app.services.export_service import ExportService

        assert inspect.iscoroutinefunction(ExportService.export_content_markdown_zip)

    def test_export_content_markdown_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("content/markdown" in p for p in paths), f"markdown route missing: {paths}"

    def test_export_content_markdown_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.get("/api/v1/content/markdown")
        assert response.status_code in (307, 401, 403)


# ============================================================================
# TestWordPressXMLParser — parse_wordpress_xml
# ============================================================================

_SAMPLE_WXR = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:wp="http://wordpress.org/export/1.2/">
  <channel>
    <title>My Blog</title>
    <wp:wxr_version>1.2</wp:wxr_version>
    <item>
      <title>Hello World</title>
      <link>/hello-world/</link>
      <dc:creator>admin</dc:creator>
      <content:encoded>This is the post body.</content:encoded>
      <wp:post_id>1</wp:post_id>
      <wp:post_name>hello-world</wp:post_name>
      <wp:status>publish</wp:status>
      <wp:post_type>post</wp:post_type>
      <category domain="category" nicename="news">News</category>
      <category domain="post_tag" nicename="intro">intro</category>
    </item>
    <item>
      <title>Draft Post</title>
      <wp:post_name>draft-post</wp:post_name>
      <wp:status>draft</wp:status>
      <wp:post_type>post</wp:post_type>
      <content:encoded>Draft content.</content:encoded>
    </item>
    <item>
      <title>Attachment</title>
      <wp:post_type>attachment</wp:post_type>
    </item>
  </channel>
</rss>"""


class TestWordPressXMLParser:
    def _parse(self):
        import asyncio

        from app.services.import_service import parse_wordpress_xml

        return asyncio.run(parse_wordpress_xml(_SAMPLE_WXR))

    def test_parse_wordpress_xml_returns_list(self):
        result = self._parse()
        assert isinstance(result, list)

    def test_parse_wordpress_xml_excludes_attachments(self):
        result = self._parse()
        # Should include 'Hello World' and 'Draft Post' but NOT the attachment
        assert len(result) == 2

    def test_parse_wordpress_xml_title(self):
        result = self._parse()
        assert result[0]["title"] == "Hello World"

    def test_parse_wordpress_xml_slug(self):
        result = self._parse()
        assert result[0]["slug"] == "hello-world"

    def test_parse_wordpress_xml_maps_publish_to_published(self):
        result = self._parse()
        assert result[0]["status"] == "published"

    def test_parse_wordpress_xml_draft_status(self):
        result = self._parse()
        assert result[1]["status"] == "draft"

    def test_parse_wordpress_xml_body(self):
        result = self._parse()
        assert "post body" in result[0]["body"]

    def test_parse_wordpress_xml_category(self):
        result = self._parse()
        assert result[0]["category"] == "News"

    def test_parse_wordpress_xml_tags(self):
        result = self._parse()
        assert "intro" in result[0]["tags"]

    def test_parse_wordpress_xml_invalid_raises(self):
        import asyncio

        from fastapi import HTTPException

        from app.services.import_service import parse_wordpress_xml

        try:
            asyncio.run(parse_wordpress_xml(b"this is not xml"))
            raise AssertionError("Expected HTTPException")
        except HTTPException as e:
            assert e.status_code == 400


# ============================================================================
# TestMarkdownParser — parse_frontmatter + parse_markdown_content
# ============================================================================

_SAMPLE_MD = b"""---
title: "My Article"
slug: my-article
status: published
author: admin
category: Technology
tags: [python, cms]
meta_description: "A great article"
---

This is the **body** of the article.
"""

_SAMPLE_MD_NO_FRONTMATTER = b"""# Just a heading

Plain markdown without frontmatter.
"""


class TestMarkdownParser:
    def _parse(self, content: bytes = _SAMPLE_MD):
        import asyncio

        from app.services.import_service import parse_markdown_content

        return asyncio.run(parse_markdown_content(content))

    def test_parse_markdown_returns_list_with_one_item(self):
        result = self._parse()
        assert isinstance(result, list)
        assert len(result) == 1

    def test_parse_markdown_title(self):
        result = self._parse()
        assert result[0]["title"] == "My Article"

    def test_parse_markdown_slug(self):
        result = self._parse()
        assert result[0]["slug"] == "my-article"

    def test_parse_markdown_status(self):
        result = self._parse()
        assert result[0]["status"] == "published"

    def test_parse_markdown_body_contains_text(self):
        result = self._parse()
        assert "body" in result[0]["body"]

    def test_parse_markdown_meta_description(self):
        result = self._parse()
        assert result[0]["meta_description"] == "A great article"

    def test_parse_markdown_no_frontmatter_returns_empty_title(self):
        result = self._parse(_SAMPLE_MD_NO_FRONTMATTER)
        assert result[0]["title"] == ""
        assert "heading" in result[0]["body"] or "Just a heading" in result[0]["body"]

    def test_parse_markdown_category(self):
        result = self._parse()
        assert result[0]["category"] == "Technology"


# ============================================================================
# TestWordPressImportRoutes — route registration
# ============================================================================


class TestWordPressImportRoutes:
    def test_wordpress_import_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("content/wordpress" in p for p in paths), f"WP import route missing: {paths}"

    def test_wordpress_import_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.post("/api/v1/content/wordpress", data={})
        assert response.status_code in (307, 401, 403, 422)

    def test_markdown_import_route_registered(self):
        from main import app

        paths = [r.path for r in app.routes]
        assert any("content/markdown" in p for p in paths), f"MD import route missing: {paths}"

    def test_markdown_import_requires_auth(self):
        from fastapi.testclient import TestClient

        from main import app

        client = TestClient(app, follow_redirects=False)
        response = client.post("/api/v1/content/markdown", data={})
        assert response.status_code in (307, 401, 403, 422)


# ============================================================================
# TestMarkdownZipStructure — in-memory ZIP validation (no DB needed)
# ============================================================================


class TestMarkdownZipStructure:
    """Test that export_content_markdown_zip produces a valid ZIP.
    Uses a mock DB session — no real DB required."""

    def test_empty_export_produces_valid_zip(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from app.services.export_service import ExportService

        # Mock DB that returns empty content list
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        zip_bytes = asyncio.run(ExportService.export_content_markdown_zip(db=mock_db))
        assert isinstance(zip_bytes, bytes)

        # Must be a valid ZIP
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert zf.namelist() == []

    def test_xml_export_produces_valid_xml(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from app.services.export_service import ExportService

        # Mock DB that returns empty content list
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        xml_str = asyncio.run(ExportService.export_content_xml(db=mock_db))
        assert isinstance(xml_str, str)
        assert "<contents" in xml_str
        assert "<?xml version" in xml_str

    def test_wordpress_export_produces_rss_structure(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from app.services.export_service import ExportService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        wxr_str = asyncio.run(ExportService.export_content_wordpress(db=mock_db))
        assert isinstance(wxr_str, str)
        assert "<rss" in wxr_str
        assert "wp:wxr_version" in wxr_str
        assert "wordpress.org/export" in wxr_str
