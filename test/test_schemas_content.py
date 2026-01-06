"""
Tests for content schemas

Tests content creation, update schemas and field validators.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.content import (
    ContentCreate,
    ContentResponse,
    ContentStatus,
    ContentUpdate,
)


class TestContentCreate:
    """Test ContentCreate schema"""

    def test_content_create_with_all_fields(self):
        """Test creating content with all fields"""
        data = {
            "title": "Test Content",
            "body": "<p>Test body</p>",
            "description": "Test description",
            "slug": "test-content",
            "meta_title": "Test Meta Title",
            "meta_description": "Test meta description",
            "meta_keywords": "test, keywords",
            "status": ContentStatus.DRAFT,
            "publish_at": datetime.now(timezone.utc),
        }
        content = ContentCreate(**data)
        assert content.title == "Test Content"
        assert content.body == "<p>Test body</p>"
        assert content.slug == "test-content"

    def test_content_create_with_minimum_fields(self):
        """Test creating content with only required fields"""
        data = {
            "title": "Test Content",
            "body": "Test body",
            "description": "Test description",
        }
        content = ContentCreate(**data)
        assert content.title == "Test Content"
        assert content.body == "Test body"
        assert content.status == ContentStatus.DRAFT  # Default value

    def test_content_create_sanitizes_title(self):
        """Test that title is sanitized"""
        data = {
            "title": "<script>alert('xss')</script>Test Title",
            "body": "Test body",
            "description": "Test description",
        }
        content = ContentCreate(**data)
        # Should strip script tags
        assert "<script>" not in content.title

    def test_content_create_sanitizes_body(self):
        """Test that body allows safe HTML"""
        data = {
            "title": "Test Title",
            "body": "<p>Safe paragraph</p><script>alert('xss')</script>",
            "description": "Test description",
        }
        content = ContentCreate(**data)
        # Should strip script tags but keep paragraph tags
        assert "<script>" not in content.body

    def test_content_create_sanitizes_slug_when_provided(self):
        """Test that slug is sanitized when provided"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "Test description",
            "slug": "<script>test-slug</script>",
        }
        content = ContentCreate(**data)
        # Slug should be plain text
        assert "<script>" not in content.slug

    def test_content_create_sanitizes_slug_when_none(self):
        """Test that None slug passes through validator"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "Test description",
            "slug": None,
        }
        content = ContentCreate(**data)
        assert content.slug is None

    def test_content_create_sanitizes_meta_title(self):
        """Test that meta_title is sanitized"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "Test description",
            "meta_title": "<b>Bold Title</b>",
        }
        content = ContentCreate(**data)
        # Meta title should strip HTML
        assert "<b>" not in content.meta_title

    def test_content_create_sanitizes_meta_title_when_none(self):
        """Test that None meta_title passes through validator"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "Test description",
            "meta_title": None,
        }
        content = ContentCreate(**data)
        assert content.meta_title is None

    def test_content_create_sanitizes_description(self):
        """Test that description is sanitized"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "<i>Italic description</i>",
        }
        content = ContentCreate(**data)
        # Description should strip HTML
        assert "<i>" not in content.description

    def test_content_create_sanitizes_meta_description_when_none(self):
        """Test that None meta_description passes through validator"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "Test description",
            "meta_description": None,
        }
        content = ContentCreate(**data)
        assert content.meta_description is None

    def test_content_create_sanitizes_meta_keywords_when_none(self):
        """Test that None meta_keywords passes through validator"""
        data = {
            "title": "Test Title",
            "body": "Test body",
            "description": "Test description",
            "meta_keywords": None,
        }
        content = ContentCreate(**data)
        assert content.meta_keywords is None


class TestContentUpdate:
    """Test ContentUpdate schema"""

    def test_content_update_with_all_fields(self):
        """Test updating content with all fields"""
        data = {
            "title": "Updated Title",
            "body": "<p>Updated body</p>",
            "slug": "updated-slug",
            "meta_title": "Updated Meta",
            "meta_description": "Updated description",
            "meta_keywords": "updated, keywords",
            "status": ContentStatus.PUBLISHED,
            "publish_at": datetime.now(timezone.utc),
        }
        content = ContentUpdate(**data)
        assert content.title == "Updated Title"
        assert content.body == "<p>Updated body</p>"

    def test_content_update_with_no_fields(self):
        """Test updating content with no fields (all None)"""
        data = {}
        content = ContentUpdate(**data)
        assert content.title is None
        assert content.body is None
        assert content.slug is None

    def test_content_update_partial_update(self):
        """Test updating only some fields"""
        data = {"title": "New Title", "status": ContentStatus.PUBLISHED}
        content = ContentUpdate(**data)
        assert content.title == "New Title"
        assert content.status == ContentStatus.PUBLISHED
        assert content.body is None  # Other fields are None

    def test_content_update_sanitizes_title_when_none(self):
        """Test that None title passes through validator"""
        data = {"title": None}
        content = ContentUpdate(**data)
        assert content.title is None

    def test_content_update_sanitizes_body_when_none(self):
        """Test that None body passes through validator"""
        data = {"body": None}
        content = ContentUpdate(**data)
        assert content.body is None

    def test_content_update_sanitizes_slug_when_none(self):
        """Test that None slug passes through validator"""
        data = {"slug": None}
        content = ContentUpdate(**data)
        assert content.slug is None

    def test_content_update_sanitizes_meta_title_when_none(self):
        """Test that None meta_title passes through validator"""
        data = {"meta_title": None}
        content = ContentUpdate(**data)
        assert content.meta_title is None

    def test_content_update_sanitizes_meta_description_when_none(self):
        """Test that None meta_description passes through validator"""
        data = {"meta_description": None}
        content = ContentUpdate(**data)
        assert content.meta_description is None

    def test_content_update_sanitizes_meta_keywords_when_none(self):
        """Test that None meta_keywords passes through validator"""
        data = {"meta_keywords": None}
        content = ContentUpdate(**data)
        assert content.meta_keywords is None

    def test_content_update_sanitizes_title_with_html(self):
        """Test that title with HTML is sanitized"""
        data = {"title": "<script>alert('xss')</script>Updated"}
        content = ContentUpdate(**data)
        assert "<script>" not in content.title

    def test_content_update_sanitizes_body_with_html(self):
        """Test that body sanitizes dangerous HTML"""
        data = {"body": "<p>Safe</p><script>alert('xss')</script>"}
        content = ContentUpdate(**data)
        assert "<script>" not in content.body


class TestContentResponse:
    """Test ContentResponse schema"""

    def test_content_response_with_all_fields(self):
        """Test content response representation"""
        data = {
            "id": 1,
            "title": "Response Content",
            "body": "<p>Response body</p>",
            "status": ContentStatus.PUBLISHED,
            "author_id": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        content = ContentResponse(**data)
        assert content.id == 1
        assert content.title == "Response Content"
        assert content.status == ContentStatus.PUBLISHED

    def test_content_response_requires_all_fields(self):
        """Test that all fields are required"""
        # Missing author_id
        data = {
            "id": 1,
            "title": "Test",
            "body": "Test",
            "status": ContentStatus.PUBLISHED,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        with pytest.raises(ValidationError) as exc_info:
            ContentResponse(**data)
        assert "author_id" in str(exc_info.value).lower()


class TestContentStatus:
    """Test ContentStatus enum"""

    def test_content_status_values(self):
        """Test that content status values are defined"""
        assert ContentStatus.DRAFT == "draft"
        assert ContentStatus.PUBLISHED == "published"

    def test_content_status_is_enum(self):
        """Test that ContentStatus is an enum"""
        assert isinstance(ContentStatus.DRAFT, str)
        assert isinstance(ContentStatus.PUBLISHED, str)

    def test_content_status_in_schema(self):
        """Test that ContentStatus works in schemas"""
        data = {
            "title": "Test",
            "body": "Test",
            "description": "Test",
            "status": ContentStatus.PUBLISHED,
        }
        content = ContentCreate(**data)
        assert content.status == ContentStatus.PUBLISHED


class TestContentSchemaValidation:
    """Test schema validation rules"""

    def test_content_create_requires_title(self):
        """Test that title is required"""
        data = {"body": "Test", "description": "Test"}
        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(**data)
        assert "title" in str(exc_info.value).lower()

    def test_content_create_requires_body(self):
        """Test that body is required"""
        data = {"title": "Test", "description": "Test"}
        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(**data)
        assert "body" in str(exc_info.value).lower()

    def test_content_create_requires_description(self):
        """Test that description is required"""
        data = {"title": "Test", "body": "Test"}
        with pytest.raises(ValidationError) as exc_info:
            ContentCreate(**data)
        assert "description" in str(exc_info.value).lower()


class TestContentSchemaExamples:
    """Test schema examples and realistic use cases"""

    def test_blog_post_creation(self):
        """Test creating a blog post"""
        data = {
            "title": "How to Use FastAPI",
            "body": "<p>FastAPI is a modern web framework...</p>",
            "description": "Learn how to use FastAPI effectively",
            "slug": "how-to-use-fastapi",
            "meta_title": "How to Use FastAPI - Tutorial",
            "meta_description": "Learn how to use FastAPI in this comprehensive tutorial",
            "meta_keywords": "fastapi, python, tutorial",
            "status": ContentStatus.DRAFT,
        }
        content = ContentCreate(**data)
        assert content.title == "How to Use FastAPI"
        assert content.status == ContentStatus.DRAFT

    def test_content_publishing_update(self):
        """Test updating content to publish it"""
        data = {
            "status": ContentStatus.PUBLISHED,
            "publish_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        content = ContentUpdate(**data)
        assert content.status == ContentStatus.PUBLISHED
        assert content.publish_at is not None
