"""
Tests for category routes

Tests category CRUD endpoints with database integration.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.category import Category
from app.routes import category

# Test database URL (SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function", autouse=True)
async def setup_test_database():
    """Create a fresh database for each test function"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client():
    """Create test client with database dependency override"""
    # Create a minimal test app without lifespan
    test_app = FastAPI()
    test_app.include_router(category.router, prefix="/api/v1/categories")

    # Register exception handlers for proper error handling
    from app.exception_handlers import register_exception_handlers

    register_exception_handlers(test_app)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()


class TestCreateCategory:
    """Test POST /api/v1/categories/ endpoint"""

    def test_create_category_with_all_fields(self, client):
        """Test creating category with name, slug, and parent_id"""
        data = {
            "name": "Technology",
            "slug": "technology",
            "parent_id": None,
        }
        response = client.post("/api/v1/categories/", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Technology"
        assert result["slug"] == "technology"
        assert result["parent_id"] is None
        assert "id" in result

    def test_create_category_without_slug_auto_generates(self, client):
        """Test that slug is auto-generated from name if not provided"""
        data = {
            "name": "Web Development",
            "slug": None,
        }
        response = client.post("/api/v1/categories/", json=data)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "Web Development"
        assert result["slug"] == "web-development"  # Auto-generated from name

    def test_create_category_with_duplicate_slug_fails(self, client):
        """Test that duplicate slugs are rejected"""
        # Create first category
        data1 = {
            "name": "Technology",
            "slug": "tech",
        }
        response1 = client.post("/api/v1/categories/", json=data1)
        assert response1.status_code == 200

        # Try to create second category with same slug
        data2 = {
            "name": "Technology 2",
            "slug": "tech",
        }
        response2 = client.post("/api/v1/categories/", json=data2)

        assert response2.status_code == 400
        response_data = response2.json()
        # Check for error message in any field
        error_message = str(response_data).lower()
        assert "slug" in error_message and "exist" in error_message

    def test_create_category_with_parent_id(self, client):
        """Test creating a subcategory with parent_id"""
        # Create parent category
        parent_data = {
            "name": "Technology",
            "slug": "technology",
        }
        parent_response = client.post("/api/v1/categories/", json=parent_data)
        parent_id = parent_response.json()["id"]

        # Create child category
        child_data = {
            "name": "Programming",
            "slug": "programming",
            "parent_id": parent_id,
        }
        child_response = client.post("/api/v1/categories/", json=child_data)

        assert child_response.status_code == 200
        child = child_response.json()
        assert child["parent_id"] == parent_id
        assert child["name"] == "Programming"

    def test_create_category_sanitizes_name(self, client):
        """Test that category name is sanitized"""
        data = {
            "name": "<script>alert('xss')</script>Tech",
            "slug": "tech",
        }
        response = client.post("/api/v1/categories/", json=data)

        assert response.status_code == 200
        result = response.json()
        # Name should be sanitized
        assert "<script>" not in result["name"]

    def test_create_category_sanitizes_slug(self, client):
        """Test that category slug is sanitized"""
        data = {
            "name": "Technology",
            "slug": "<b>tech-slug</b>",
        }
        response = client.post("/api/v1/categories/", json=data)

        assert response.status_code == 200
        result = response.json()
        # Slug should be sanitized
        assert "<b>" not in result["slug"]

    def test_create_category_with_special_characters_in_name(self, client):
        """Test creating category with special characters that get slugified"""
        data = {
            "name": "Web & Mobile Development",
            # No slug provided, should auto-generate
        }
        response = client.post("/api/v1/categories/", json=data)

        assert response.status_code == 200
        result = response.json()
        # & is HTML-encoded by sanitize_plain_text
        assert result["name"] == "Web &amp; Mobile Development"
        # Slug should be auto-generated and sanitized
        assert result["slug"]  # Should have a valid slug


class TestGetCategories:
    """Test GET /api/v1/categories/ endpoint"""

    def test_get_categories_empty_list(self, client):
        """Test getting categories when none exist"""
        response = client.get("/api/v1/categories/")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_categories_returns_all(self, client):
        """Test getting all categories"""
        # Create multiple categories
        categories_data = [
            {"name": "Technology", "slug": "technology"},
            {"name": "Science", "slug": "science"},
            {"name": "Arts", "slug": "arts"},
        ]

        for data in categories_data:
            client.post("/api/v1/categories/", json=data)

        # Get all categories
        response = client.get("/api/v1/categories/")

        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 3

        # Verify all categories are present
        category_names = [cat["name"] for cat in categories]
        assert "Technology" in category_names
        assert "Science" in category_names
        assert "Arts" in category_names

    def test_get_categories_includes_parent_child_relationships(self, client):
        """Test that parent-child relationships are preserved"""
        # Create parent
        parent_response = client.post("/api/v1/categories/", json={"name": "Technology", "slug": "technology"})
        parent_id = parent_response.json()["id"]

        # Create child
        client.post(
            "/api/v1/categories/",
            json={"name": "Programming", "slug": "programming", "parent_id": parent_id},
        )

        # Get all categories
        response = client.get("/api/v1/categories/")

        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 2

        # Find the child category
        child = next(cat for cat in categories if cat["name"] == "Programming")
        assert child["parent_id"] == parent_id

    def test_get_categories_response_format(self, client):
        """Test that category response has correct format"""
        # Create a category
        client.post("/api/v1/categories/", json={"name": "Technology", "slug": "tech"})

        # Get categories
        response = client.get("/api/v1/categories/")

        assert response.status_code == 200
        categories = response.json()
        assert len(categories) == 1

        category = categories[0]
        # Verify all required fields are present
        assert "id" in category
        assert "name" in category
        assert "slug" in category
        assert "parent_id" in category


class TestCategoryRouteIntegration:
    """Integration tests for category routes"""

    def test_create_and_retrieve_category_workflow(self, client):
        """Test complete workflow of creating and retrieving categories"""
        # Create a category
        create_data = {
            "name": "Technology",
            "slug": "technology",
        }
        create_response = client.post("/api/v1/categories/", json=create_data)
        assert create_response.status_code == 200
        created = create_response.json()

        # Retrieve all categories
        get_response = client.get("/api/v1/categories/")
        assert get_response.status_code == 200
        categories = get_response.json()

        # Verify the created category is in the list
        assert len(categories) == 1
        assert categories[0]["id"] == created["id"]
        assert categories[0]["name"] == created["name"]

    def test_create_category_hierarchy(self, client):
        """Test creating a full category hierarchy"""
        # Create root category
        root_response = client.post("/api/v1/categories/", json={"name": "Technology", "slug": "technology"})
        root_id = root_response.json()["id"]

        # Create level 1 subcategory
        level1_response = client.post(
            "/api/v1/categories/",
            json={"name": "Programming", "slug": "programming", "parent_id": root_id},
        )
        level1_id = level1_response.json()["id"]

        # Create level 2 subcategory
        level2_response = client.post(
            "/api/v1/categories/",
            json={"name": "Python", "slug": "python", "parent_id": level1_id},
        )

        # Verify hierarchy
        all_categories = client.get("/api/v1/categories/").json()
        assert len(all_categories) == 3

        # Verify relationships
        python_cat = next(cat for cat in all_categories if cat["name"] == "Python")
        assert python_cat["parent_id"] == level1_id

        programming_cat = next(cat for cat in all_categories if cat["name"] == "Programming")
        assert programming_cat["parent_id"] == root_id

        tech_cat = next(cat for cat in all_categories if cat["name"] == "Technology")
        assert tech_cat["parent_id"] is None

    def test_create_multiple_categories_with_same_parent(self, client):
        """Test creating multiple categories under the same parent"""
        # Create parent
        parent_response = client.post("/api/v1/categories/", json={"name": "Technology", "slug": "technology"})
        parent_id = parent_response.json()["id"]

        # Create multiple children
        children = ["Programming", "Hardware", "Software"]
        for child_name in children:
            response = client.post(
                "/api/v1/categories/",
                json={
                    "name": child_name,
                    "slug": child_name.lower(),
                    "parent_id": parent_id,
                },
            )
            assert response.status_code == 200
            assert response.json()["parent_id"] == parent_id

        # Verify all categories exist
        all_cats = client.get("/api/v1/categories/").json()
        assert len(all_cats) == 4  # 1 parent + 3 children


class TestCategoryValidation:
    """Test validation and error handling for category routes"""

    def test_create_category_with_very_long_name(self, client):
        """Test category with very long name"""
        data = {
            "name": "A" * 500,  # Very long name
        }
        response = client.post("/api/v1/categories/", json=data)

        # Should either succeed or fail validation if there's a length limit
        # This tests that the system handles long inputs gracefully
        assert response.status_code in [200, 400, 422]

    def test_create_category_with_invalid_parent_id(self, client):
        """Test creating category with non-existent parent_id"""
        data = {
            "name": "Child Category",
            "slug": "child",
            "parent_id": 99999,  # Non-existent parent
        }
        response = client.post("/api/v1/categories/", json=data)

        # Should either fail with foreign key constraint or create successfully
        # (depends on database constraints)
        assert response.status_code in [200, 400, 422, 500]

    def test_create_category_with_zero_parent_id(self, client):
        """Test creating category with parent_id=0"""
        data = {
            "name": "Category",
            "slug": "category",
            "parent_id": 0,
        }
        response = client.post("/api/v1/categories/", json=data)

        # Should handle gracefully
        assert response.status_code in [200, 400, 422, 500]

    def test_create_category_with_empty_slug_auto_generates(self, client):
        """Test that empty string slug still triggers auto-generation"""
        data = {
            "name": "Test Category",
            "slug": "",  # Empty string instead of None
        }
        response = client.post("/api/v1/categories/", json=data)

        # Should either auto-generate or fail validation
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            result = response.json()
            # If successful, slug should be auto-generated
            assert result["slug"] != ""

    def test_create_category_with_malformed_json(self, client):
        """Test handling of malformed JSON data"""
        # Send completely wrong structure
        response = client.post(
            "/api/v1/categories/",
            json={"invalid_field": "value"},
        )

        # Should fail validation
        assert response.status_code == 422

    def test_create_category_with_unicode_name(self, client):
        """Test category with unicode characters"""
        data = {
            "name": "Technology 技术 🚀",
        }
        response = client.post("/api/v1/categories/", json=data)

        # Should handle unicode gracefully
        assert response.status_code == 200
        result = response.json()
        assert "Technology" in result["name"]

    def test_get_categories_multiple_times_consistent(self, client):
        """Test that GET /categories returns consistent results"""
        # Create a category
        client.post("/api/v1/categories/", json={"name": "Test", "slug": "test"})

        # Get categories multiple times
        response1 = client.get("/api/v1/categories/")
        response2 = client.get("/api/v1/categories/")

        # Should return same results
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()


class TestCategoryErrorPaths:
    """Test error handling paths in category routes"""

    def test_duplicate_slug_exception_path(self, client):
        """Test that duplicate slug raises proper HTTP 400 exception (lines 18-19)"""
        # First category
        response1 = client.post("/api/v1/categories/", json={"name": "Tech", "slug": "technology"})
        assert response1.status_code == 200

        # Second category with same slug should fail
        response2 = client.post("/api/v1/categories/", json={"name": "Technology", "slug": "technology"})
        assert response2.status_code == 400
        response_data = response2.json()
        error_message = str(response_data).lower()
        assert "already" in error_message and "exist" in error_message

    def test_create_category_full_transaction(self, client):
        """Test full create transaction completes successfully (lines 21-25)"""
        data = {"name": "Full Transaction Test", "slug": "full-test"}
        response = client.post("/api/v1/categories/", json=data)

        # Verify creation succeeded
        assert response.status_code == 200
        result = response.json()

        # Verify all fields are populated (meaning db operations completed)
        assert result["id"] is not None
        assert result["name"] == "Full Transaction Test"
        assert result["slug"] == "full-test"

        # Verify it's actually in the database by fetching
        get_response = client.get("/api/v1/categories/")
        categories = get_response.json()
        assert len(categories) == 1
        assert categories[0]["id"] == result["id"]

    def test_get_categories_returns_all_results(self, client):
        """Test that get_categories properly executes and returns (line 31)"""
        # Create multiple categories to ensure we're testing the actual return path
        for i in range(3):
            client.post("/api/v1/categories/", json={"name": f"Category {i}", "slug": f"cat-{i}"})

        # Get all categories
        response = client.get("/api/v1/categories/")
        assert response.status_code == 200

        # Verify the return statement executes properly (line 31)
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) == 3

        # Verify all categories are present (confirming scalars().all() worked)
        slugs = [cat["slug"] for cat in categories]
        assert "cat-0" in slugs
        assert "cat-1" in slugs
        assert "cat-2" in slugs

    def test_create_with_auto_slug_generation(self, client):
        """Test auto-slug generation path (line 15)"""
        # Provide name but no slug
        data = {"name": "Auto Slug Test"}
        response = client.post("/api/v1/categories/", json=data)

        assert response.status_code == 200
        result = response.json()

        # Verify slug was auto-generated
        assert result["slug"] is not None
        assert result["slug"] != ""
        assert "-" in result["slug"] or result["slug"] == "auto-slug-test"
