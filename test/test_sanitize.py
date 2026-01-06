"""
Tests for input sanitization utilities

Tests HTML sanitization, XSS prevention, and input validation.
"""

import pytest

from app.utils.sanitize import (
    sanitize_comment,
    sanitize_content_body,
    sanitize_content_title,
    sanitize_email,
    sanitize_filename,
    sanitize_html,
    sanitize_meta_description,
    sanitize_plain_text,
    sanitize_rich_content,
    sanitize_url,
    sanitize_username,
)


class TestPlainTextSanitization:
    """Test plain text sanitization (strip all HTML)"""

    def test_strips_script_tags(self):
        dirty = "<script>alert('xss')</script>Hello World"
        clean = sanitize_plain_text(dirty)
        assert "<script>" not in clean
        assert "Hello World" in clean

    def test_strips_all_html_tags(self):
        dirty = "<div><p>Hello <strong>World</strong></p></div>"
        clean = sanitize_plain_text(dirty)
        assert "<" not in clean
        assert ">" not in clean
        assert "Hello World" in clean

    def test_normalizes_whitespace(self):
        dirty = "Hello    \n\n  World"
        clean = sanitize_plain_text(dirty)
        assert clean == "Hello World"

    def test_handles_none_input(self):
        clean = sanitize_plain_text(None)
        assert clean == ""

    def test_handles_empty_string(self):
        clean = sanitize_plain_text("")
        assert clean == ""


class TestRichContentSanitization:
    """Test rich content sanitization (allow safe HTML)"""

    def test_preserves_safe_html(self):
        safe = "<p>This is <strong>bold</strong> text</p>"
        clean = sanitize_rich_content(safe)
        assert "<p>" in clean
        assert "<strong>" in clean
        assert "bold" in clean

    def test_removes_script_tags(self):
        dangerous = "<script>alert('xss')</script><p>Safe content</p>"
        clean = sanitize_rich_content(dangerous)
        assert "<script>" not in clean
        assert "<p>Safe content</p>" in clean

    def test_removes_onclick_attributes(self):
        dangerous = "<div onclick=\"alert('xss')\">Click me</div>"
        clean = sanitize_rich_content(dangerous)
        assert "onclick" not in clean
        assert "Click me" in clean

    def test_allows_safe_links(self):
        safe = '<a href="https://example.com" title="Link">Click</a>'
        clean = sanitize_rich_content(safe)
        assert '<a href="https://example.com"' in clean
        assert "Click" in clean

    def test_removes_javascript_urls(self):
        dangerous = "<a href=\"javascript:alert('xss')\">Click</a>"
        clean = sanitize_rich_content(dangerous)
        assert "javascript:" not in clean

    def test_preserves_headings(self):
        content = "<h1>Title</h1><h2>Subtitle</h2><p>Content</p>"
        clean = sanitize_rich_content(content)
        assert "<h1>" in clean
        assert "<h2>" in clean
        assert "Title" in clean

    def test_preserves_lists(self):
        content = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        clean = sanitize_rich_content(content)
        assert "<ul>" in clean
        assert "<li>" in clean

    def test_preserves_code_blocks(self):
        content = '<pre><code class="python">print("hello")</code></pre>'
        clean = sanitize_rich_content(content)
        assert "<pre>" in clean
        assert "<code" in clean


class TestCommentSanitization:
    """Test comment sanitization (limited HTML)"""

    def test_allows_basic_formatting(self):
        comment = "<p>This is <strong>bold</strong> and <em>italic</em></p>"
        clean = sanitize_comment(comment)
        assert "<strong>" in clean
        assert "<em>" in clean

    def test_removes_headings(self):
        comment = "<h1>Big Title</h1><p>Normal text</p>"
        clean = sanitize_comment(comment)
        assert "<h1>" not in clean
        assert "Big Title" in clean
        assert "<p>" in clean

    def test_removes_images(self):
        comment = '<p>Text<img src="image.jpg">More text</p>'
        clean = sanitize_comment(comment)
        assert "<img" not in clean
        assert "Text" in clean


class TestURLSanitization:
    """Test URL sanitization and validation"""

    def test_allows_https_urls(self):
        url = "https://example.com/page"
        clean = sanitize_url(url)
        assert clean == "https://example.com/page"

    def test_allows_http_urls(self):
        url = "http://example.com/page"
        clean = sanitize_url(url)
        assert clean == "http://example.com/page"

    def test_blocks_javascript_urls(self):
        url = "javascript:alert('xss')"
        clean = sanitize_url(url)
        assert clean is None

    def test_blocks_data_urls(self):
        url = "data:text/html,<script>alert('xss')</script>"
        clean = sanitize_url(url)
        assert clean is None

    def test_blocks_vbscript_urls(self):
        url = "vbscript:msgbox('xss')"
        clean = sanitize_url(url)
        assert clean is None

    def test_adds_https_to_urls_without_protocol(self):
        url = "example.com/page"
        clean = sanitize_url(url)
        assert clean == "https://example.com/page"

    def test_handles_none_input(self):
        clean = sanitize_url(None)
        assert clean is None

    def test_strips_whitespace(self):
        url = "  https://example.com  "
        clean = sanitize_url(url)
        assert clean == "https://example.com"


class TestFilenameSanitization:
    """Test filename sanitization to prevent directory traversal"""

    def test_removes_path_separators(self):
        filename = "../../../etc/passwd"
        clean = sanitize_filename(filename)
        assert "/" not in clean
        assert "\\" not in clean
        assert ".." in clean  # Dots are allowed, just not as path separators

    def test_removes_dangerous_characters(self):
        filename = 'file<>:"|?*.txt'
        clean = sanitize_filename(filename)
        assert "<" not in clean
        assert ">" not in clean
        assert ":" not in clean

    def test_preserves_valid_filename(self):
        filename = "document-2024.pdf"
        clean = sanitize_filename(filename)
        assert clean == "document-2024.pdf"

    def test_limits_length(self):
        filename = "a" * 300 + ".txt"
        clean = sanitize_filename(filename)
        assert len(clean) <= 255

    def test_handles_none_input(self):
        clean = sanitize_filename(None)
        assert clean == "unnamed"

    def test_handles_empty_string(self):
        clean = sanitize_filename("")
        assert clean == "unnamed"


class TestUsernameSanitization:
    """Test username sanitization"""

    def test_removes_html_tags(self):
        username = "<script>user</script>testuser"
        clean = sanitize_username(username)
        assert "<" not in clean
        assert ">" not in clean
        assert "testuser" in clean

    def test_allows_alphanumeric_and_common_chars(self):
        username = "user.name_123-test"
        clean = sanitize_username(username)
        assert clean == "user.name_123-test"

    def test_removes_special_characters(self):
        username = "user@#$%name"
        clean = sanitize_username(username)
        assert "@" not in clean
        assert "#" not in clean
        assert "username" in clean

    def test_limits_length(self):
        username = "a" * 100
        clean = sanitize_username(username)
        assert len(clean) == 50

    def test_handles_none_input(self):
        clean = sanitize_username(None)
        assert clean == ""


class TestEmailSanitization:
    """Test email sanitization"""

    def test_preserves_valid_email(self):
        email = "user@example.com"
        clean = sanitize_email(email)
        assert "@" in clean
        assert "example.com" in clean

    def test_strips_whitespace(self):
        email = "  user@example.com  "
        clean = sanitize_email(email)
        assert clean.strip() == clean

    def test_handles_none_input(self):
        clean = sanitize_email(None)
        assert clean == ""


class TestContentSpecificSanitizers:
    """Test pre-configured sanitizers for specific content types"""

    def test_sanitize_content_title_strips_html(self):
        title = "<script>alert('xss')</script>My Title"
        clean = sanitize_content_title(title)
        assert "<script>" not in clean
        assert "My Title" in clean

    def test_sanitize_content_body_allows_safe_html(self):
        body = "<p>This is <strong>content</strong></p><script>bad()</script>"
        clean = sanitize_content_body(body)
        assert "<p>" in clean
        assert "<strong>" in clean
        assert "<script>" not in clean

    def test_sanitize_meta_description_strips_html(self):
        meta = "<b>Bold description</b>"
        clean = sanitize_meta_description(meta)
        assert "<b>" not in clean
        assert "Bold description" in clean


class TestSchemaIntegration:
    """Test that Pydantic schemas apply sanitization automatically"""

    def test_content_schema_sanitizes_title(self):
        from app.schemas.content import ContentCreate

        content = ContentCreate(
            title="<script>alert('xss')</script>My Title",
            body="<p>Content</p>",
            description="Description",
        )

        assert "<script>" not in content.title
        assert "My Title" in content.title

    def test_content_schema_sanitizes_body(self):
        from app.schemas.content import ContentCreate

        content = ContentCreate(
            title="Title",
            body="<p>Good content</p><script>bad()</script>",
            description="Description",
        )

        assert "<p>" in content.body
        assert "<script>" not in content.body or "&lt;script&gt;" in content.body

    def test_user_schema_sanitizes_username(self):
        from app.schemas.user import UserCreate

        user = UserCreate(
            username="<script>user</script>testuser",
            password="password123",  # nosec B106
            email="test@example.com",
        )

        assert "<script>" not in user.username
        assert "testuser" in user.username

    def test_category_schema_sanitizes_name(self):
        from app.schemas.category import CategoryCreate

        category = CategoryCreate(name="<b>Category</b>Name")

        assert "<b>" not in category.name
        assert "CategoryName" in category.name


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_unicode_characters_preserved(self):
        text = "Hello 世界 🌍"
        clean = sanitize_plain_text(text)
        assert "世界" in clean
        assert "🌍" in clean

    def test_nested_html_tags(self):
        dirty = "<div><p><span><strong>Text</strong></span></p></div>"
        clean = sanitize_plain_text(dirty)
        assert "<" not in clean
        assert "Text" in clean

    def test_malformed_html(self):
        dirty = "<div<p>Text</p>"
        clean = sanitize_plain_text(dirty)
        assert "Text" in clean

    def test_html_entities(self):
        text = "AT&amp;T &lt;test&gt;"
        clean = sanitize_plain_text(text)
        # Entities should be decoded or preserved
        assert "AT" in clean
        assert "T" in clean

    def test_empty_tags(self):
        html = "<p></p><strong></strong>Text"
        clean = sanitize_rich_content(html)
        assert "Text" in clean
