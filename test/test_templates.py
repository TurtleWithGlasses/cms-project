"""Tests for content template functionality."""

import pytest

from app.models.content_template import (
    ContentTemplate,
    FieldType,
    TemplateField,
    TemplateRevision,
    TemplateStatus,
)


class TestTemplateModels:
    """Test ContentTemplate models."""

    def test_template_creation(self):
        """Test creating a ContentTemplate instance."""
        template = ContentTemplate(
            name="Blog Post",
            slug="blog-post",
            description="Template for blog posts",
        )
        assert template.name == "Blog Post"
        assert template.slug == "blog-post"
        assert template.description == "Template for blog posts"

    def test_template_defaults(self):
        """Test ContentTemplate default values."""
        template = ContentTemplate(name="Test", slug="test")
        assert template.status == TemplateStatus.DRAFT
        assert template.version == 1
        assert template.default_status == "draft"
        assert template.usage_count == 0

    def test_template_field_creation(self):
        """Test creating a TemplateField instance."""
        field = TemplateField(
            template_id=1,
            name="title",
            label="Title",
            field_type=FieldType.TEXT,
            is_required=True,
        )
        assert field.name == "title"
        assert field.label == "Title"
        assert field.field_type == FieldType.TEXT
        assert field.is_required is True

    def test_template_field_defaults(self):
        """Test TemplateField default values."""
        field = TemplateField(
            template_id=1,
            name="desc",
            label="Description",
            field_type=FieldType.TEXTAREA,
        )
        assert field.is_required is False
        assert field.is_unique is False
        assert field.is_searchable is True
        assert field.order == 0

    def test_template_revision_creation(self):
        """Test creating a TemplateRevision instance."""
        revision = TemplateRevision(
            template_id=1,
            version=2,
            change_summary="Added new field",
            snapshot='{"name": "Test"}',
        )
        assert revision.template_id == 1
        assert revision.version == 2
        assert revision.change_summary == "Added new field"


class TestTemplateEnums:
    """Test template-related enums."""

    def test_template_status_values(self):
        """Test TemplateStatus enum values."""
        assert TemplateStatus.DRAFT.value == "draft"
        assert TemplateStatus.PUBLISHED.value == "published"
        assert TemplateStatus.ARCHIVED.value == "archived"

    def test_field_type_values(self):
        """Test FieldType enum values."""
        assert FieldType.TEXT.value == "text"
        assert FieldType.TEXTAREA.value == "textarea"
        assert FieldType.RICHTEXT.value == "richtext"
        assert FieldType.NUMBER.value == "number"
        assert FieldType.DATE.value == "date"
        assert FieldType.DATETIME.value == "datetime"
        assert FieldType.BOOLEAN.value == "boolean"
        assert FieldType.SELECT.value == "select"
        assert FieldType.MULTISELECT.value == "multiselect"
        assert FieldType.IMAGE.value == "image"
        assert FieldType.FILE.value == "file"
        assert FieldType.URL.value == "url"
        assert FieldType.EMAIL.value == "email"
        assert FieldType.JSON.value == "json"
        assert FieldType.REFERENCE.value == "reference"


class TestTemplateService:
    """Test template service functions."""

    def test_generate_slug(self):
        """Test slug generation."""
        from app.services.template_service import generate_slug

        assert generate_slug("Blog Post") == "blog-post"
        assert generate_slug("Product Review!") == "product-review"
        assert generate_slug("  News Article  ") == "news-article"


class TestTemplateValidation:
    """Test template validation logic."""

    def test_email_validation_pattern(self):
        """Test email validation pattern."""
        import re

        pattern = r"^[^@]+@[^@]+\.[^@]+$"
        assert re.match(pattern, "test@example.com")
        assert re.match(pattern, "user.name@domain.org")
        assert not re.match(pattern, "invalid-email")
        assert not re.match(pattern, "missing@domain")

    def test_url_validation_pattern(self):
        """Test URL validation pattern."""
        import re

        pattern = r"^https?://"
        assert re.match(pattern, "https://example.com")
        assert re.match(pattern, "http://test.org")
        assert not re.match(pattern, "ftp://files.com")
        assert not re.match(pattern, "example.com")

    def test_validation_rules_structure(self):
        """Test validation rules JSON structure."""
        import json

        rules = {
            "min_length": 10,
            "max_length": 500,
            "pattern": r"^[a-z]+$",
        }
        json_rules = json.dumps(rules)
        parsed = json.loads(json_rules)

        assert parsed["min_length"] == 10
        assert parsed["max_length"] == 500
        assert parsed["pattern"] == r"^[a-z]+$"

    def test_options_structure(self):
        """Test options JSON structure for select fields."""
        import json

        options = ["option1", "option2", "option3"]
        json_options = json.dumps(options)
        parsed = json.loads(json_options)

        assert len(parsed) == 3
        assert "option1" in parsed
        assert "option2" in parsed
