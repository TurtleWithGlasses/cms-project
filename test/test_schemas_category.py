"""
Tests for category schemas

Tests category creation and response schemas with field validators.
"""

import pytest
from pydantic import ValidationError

from app.schemas.category import CategoryCreate, CategoryResponse


class TestCategoryCreate:
    """Test CategoryCreate schema"""

    def test_category_create_with_name_only(self):
        """Test creating category with only name"""
        data = {"name": "Technology"}
        category = CategoryCreate(**data)
        assert category.name == "Technology"
        assert category.slug is None
        assert category.parent_id is None

    def test_category_create_with_all_fields(self):
        """Test creating category with all fields"""
        data = {
            "name": "Technology",
            "slug": "technology",
            "parent_id": 1,
        }
        category = CategoryCreate(**data)
        assert category.name == "Technology"
        assert category.slug == "technology"
        assert category.parent_id == 1

    def test_category_create_sanitizes_name(self):
        """Test that name is sanitized"""
        data = {"name": "<script>Technology</script>"}
        category = CategoryCreate(**data)
        # Name should be sanitized
        assert "<script>" not in category.name

    def test_category_create_sanitizes_slug(self):
        """Test that slug is sanitized"""
        data = {
            "name": "Technology",
            "slug": "<b>technology</b>",
        }
        category = CategoryCreate(**data)
        # Slug should be sanitized
        assert "<b>" not in category.slug

    def test_category_create_with_none_slug(self):
        """Test that None slug passes through validator"""
        data = {
            "name": "Technology",
            "slug": None,
        }
        category = CategoryCreate(**data)
        assert category.slug is None

    def test_category_create_with_none_parent_id(self):
        """Test that None parent_id is accepted"""
        data = {
            "name": "Technology",
            "parent_id": None,
        }
        category = CategoryCreate(**data)
        assert category.parent_id is None

    def test_category_create_requires_name(self):
        """Test that name is required"""
        data = {"slug": "technology"}
        with pytest.raises(ValidationError) as exc_info:
            CategoryCreate(**data)
        assert "name" in str(exc_info.value).lower()

    def test_category_create_with_numeric_parent_id(self):
        """Test category with parent relationship"""
        data = {
            "name": "Programming",
            "slug": "programming",
            "parent_id": 5,
        }
        category = CategoryCreate(**data)
        assert category.parent_id == 5

    def test_category_create_with_html_in_name(self):
        """Test that HTML is stripped from name"""
        data = {"name": "<strong>Bold Category</strong>"}
        category = CategoryCreate(**data)
        assert "<strong>" not in category.name
        assert "Bold Category" in category.name or "Bold" in category.name

    def test_category_create_with_empty_string_slug(self):
        """Test that empty string slug is handled"""
        data = {
            "name": "Technology",
            "slug": "",
        }
        category = CategoryCreate(**data)
        # Empty string should be sanitized
        assert category.slug is not None


class TestCategoryResponse:
    """Test CategoryResponse schema"""

    def test_category_response_with_all_fields(self):
        """Test category response with all fields"""
        data = {
            "id": 1,
            "name": "Technology",
            "slug": "technology",
            "parent_id": None,
        }
        category = CategoryResponse(**data)
        assert category.id == 1
        assert category.name == "Technology"
        assert category.slug == "technology"
        assert category.parent_id is None

    def test_category_response_with_parent(self):
        """Test category response with parent category"""
        data = {
            "id": 2,
            "name": "Programming",
            "slug": "programming",
            "parent_id": 1,
        }
        category = CategoryResponse(**data)
        assert category.id == 2
        assert category.parent_id == 1

    def test_category_response_requires_id(self):
        """Test that id is required"""
        data = {
            "name": "Technology",
            "slug": "technology",
            "parent_id": None,
        }
        with pytest.raises(ValidationError) as exc_info:
            CategoryResponse(**data)
        assert "id" in str(exc_info.value).lower()

    def test_category_response_requires_name(self):
        """Test that name is required"""
        data = {
            "id": 1,
            "slug": "technology",
            "parent_id": None,
        }
        with pytest.raises(ValidationError) as exc_info:
            CategoryResponse(**data)
        assert "name" in str(exc_info.value).lower()

    def test_category_response_requires_slug(self):
        """Test that slug is required"""
        data = {
            "id": 1,
            "name": "Technology",
            "parent_id": None,
        }
        with pytest.raises(ValidationError) as exc_info:
            CategoryResponse(**data)
        assert "slug" in str(exc_info.value).lower()

    def test_category_response_from_attributes(self):
        """Test that from_attributes config works"""

        # Mock object with attributes
        class MockCategory:
            def __init__(self):
                self.id = 1
                self.name = "Technology"
                self.slug = "technology"
                self.parent_id = None

        mock_obj = MockCategory()
        category = CategoryResponse.model_validate(mock_obj)
        assert category.id == 1
        assert category.name == "Technology"


class TestCategorySchemaIntegration:
    """Test category schema integration scenarios"""

    def test_create_root_category(self):
        """Test creating a root category (no parent)"""
        data = {
            "name": "Technology",
            "slug": "technology",
            "parent_id": None,
        }
        category = CategoryCreate(**data)
        assert category.parent_id is None
        assert category.name == "Technology"

    def test_create_subcategory(self):
        """Test creating a subcategory with parent"""
        data = {
            "name": "Web Development",
            "slug": "web-development",
            "parent_id": 1,
        }
        category = CategoryCreate(**data)
        assert category.parent_id == 1
        assert category.name == "Web Development"

    def test_category_hierarchy(self):
        """Test multiple levels of category hierarchy"""
        # Root category
        root = CategoryCreate(name="Technology", slug="technology", parent_id=None)

        # First level subcategory
        sub1 = CategoryCreate(name="Programming", slug="programming", parent_id=1)

        # Second level subcategory
        sub2 = CategoryCreate(name="Python", slug="python", parent_id=2)

        assert root.parent_id is None
        assert sub1.parent_id == 1
        assert sub2.parent_id == 2

    def test_sanitization_consistency(self):
        """Test that sanitization is consistent"""
        test_input = "<script>alert('xss')</script>Category"

        # Test name sanitization
        cat1 = CategoryCreate(name=test_input)
        # Test slug sanitization
        cat2 = CategoryCreate(name="Test", slug=test_input)

        # Both should remove script tags
        assert "<script>" not in cat1.name
        assert "<script>" not in cat2.slug
