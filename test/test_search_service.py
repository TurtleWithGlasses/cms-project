"""
Tests for Search Service

Tests search functionality including full-text search, filtering, and pagination.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_category, create_test_content, create_test_tag

from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.tag import Tag
from app.models.user import User
from app.services.search_service import SearchService, search_service


class TestSearchService:
    """Test search service functionality"""

    @pytest.fixture
    def search_svc(self):
        """Create search service instance"""
        return SearchService()

    @pytest.mark.asyncio
    async def test_search_content_by_query(self, async_db_session, test_user):
        """Test basic text search"""
        # Create test content
        content1 = await create_test_content(
            async_db_session, title="Python Tutorial", body="Learn Python programming", author_id=test_user.id
        )
        content2 = await create_test_content(
            async_db_session, title="JavaScript Guide", body="JavaScript fundamentals", author_id=test_user.id
        )

        # Search for Python
        results, total = await search_service.search_content(db=async_db_session, query="python", limit=10, offset=0)

        assert total >= 1
        assert any("python" in c.title.lower() or "python" in c.body.lower() for c in results)

    @pytest.mark.asyncio
    async def test_search_content_by_status(self, async_db_session, test_user):
        """Test filtering by status"""
        # Create content with different statuses
        draft = await create_test_content(
            async_db_session,
            title="Draft Post",
            body="Draft content",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )
        published = await create_test_content(
            async_db_session,
            title="Published Post",
            body="Published content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        # Search for published only
        results, total = await search_service.search_content(
            db=async_db_session, status="published", limit=10, offset=0
        )

        assert all(c.status == ContentStatus.PUBLISHED for c in results)

    @pytest.mark.asyncio
    async def test_search_content_by_author(self, async_db_session, test_user, session_manager):
        """Test filtering by author"""
        # Create another user
        from app.models.user import Role

        role_result = await async_db_session.execute(select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        other_user = User(email="other@example.com", username="otheruser", hashed_password="hashed", role_id=role.id)
        async_db_session.add(other_user)
        await async_db_session.commit()
        await async_db_session.refresh(other_user)

        # Create content for both users
        content1 = await create_test_content(
            async_db_session, title="User1 Post", body="Content by user1", author_id=test_user.id
        )
        content2 = await create_test_content(
            async_db_session, title="User2 Post", body="Content by user2", author_id=other_user.id
        )

        # Search by author
        results, total = await search_service.search_content(
            db=async_db_session, author_id=test_user.id, limit=10, offset=0
        )

        assert all(c.author_id == test_user.id for c in results)

    @pytest.mark.asyncio
    async def test_search_content_pagination(self, async_db_session, test_user):
        """Test pagination works correctly"""
        # Create multiple content items
        for i in range(15):
            await create_test_content(async_db_session, title=f"Post {i}", body=f"Content {i}", author_id=test_user.id)

        # Get first page
        results_page1, total = await search_service.search_content(db=async_db_session, limit=10, offset=0)

        # Get second page
        results_page2, _ = await search_service.search_content(db=async_db_session, limit=10, offset=10)

        assert len(results_page1) == 10
        assert len(results_page2) >= 5
        assert total >= 15

    @pytest.mark.asyncio
    async def test_search_content_sorting(self, async_db_session, test_user):
        """Test sorting by different fields"""
        # Create content with different titles
        await create_test_content(async_db_session, title="AAA Post", body="Content", author_id=test_user.id)
        await create_test_content(async_db_session, title="ZZZ Post", body="Content", author_id=test_user.id)
        await create_test_content(async_db_session, title="MMM Post", body="Content", author_id=test_user.id)

        # Sort ascending by title
        results_asc, _ = await search_service.search_content(
            db=async_db_session, sort_by="title", sort_order="asc", limit=10, offset=0
        )

        # Sort descending by title
        results_desc, _ = await search_service.search_content(
            db=async_db_session, sort_by="title", sort_order="desc", limit=10, offset=0
        )

        # Check order (comparing just the first result if available)
        if len(results_asc) > 0 and len(results_desc) > 0:
            assert results_asc[0].title <= results_asc[-1].title  # Ascending
            assert results_desc[0].title >= results_desc[-1].title  # Descending

    @pytest.mark.asyncio
    async def test_search_by_tags(self, async_db_session, test_user):
        """Test search by tag names"""
        # Create tags
        tag1 = await create_test_tag(async_db_session, name="python")
        tag2 = await create_test_tag(async_db_session, name="tutorial")

        # Create content with tags
        content = await create_test_content(
            async_db_session, title="Python Tutorial", body="Learn Python", author_id=test_user.id
        )
        content.tags.append(tag1)
        content.tags.append(tag2)
        await async_db_session.commit()

        # Search by tag names
        results, total = await search_service.search_by_tags(
            db=async_db_session, tag_names=["python"], limit=10, offset=0
        )

        assert total >= 1
        assert any(c.id == content.id for c in results)

    @pytest.mark.asyncio
    async def test_search_by_category(self, async_db_session, test_user):
        """Test search by category name"""
        # Create category
        category = await create_test_category(async_db_session, name="Tutorials")

        # Create content in category
        content = await create_test_content(
            async_db_session,
            title="Tutorial Post",
            body="Tutorial content",
            author_id=test_user.id,
            category_id=category.id,
        )

        # Search by category name
        results, total = await search_service.search_by_category(
            db=async_db_session, category_name="Tutorials", limit=10, offset=0
        )

        assert total >= 1
        assert any(c.id == content.id for c in results)

    @pytest.mark.asyncio
    async def test_search_by_nonexistent_category(self, async_db_session):
        """Test search by non-existent category returns empty"""
        results, total = await search_service.search_by_category(
            db=async_db_session, category_name="NonExistentCategory", limit=10, offset=0
        )

        assert total == 0
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_popular_tags(self, async_db_session, test_user):
        """Test getting popular tags"""
        # Create tags and content
        tag1 = await create_test_tag(async_db_session, name="popular")
        tag2 = await create_test_tag(async_db_session, name="rare")

        # Create multiple content with popular tag
        for i in range(5):
            content = await create_test_content(
                async_db_session, title=f"Post {i}", body="Content", author_id=test_user.id
            )
            content.tags.append(tag1)

        # Create one content with rare tag
        content = await create_test_content(async_db_session, title="Rare Post", body="Content", author_id=test_user.id)
        content.tags.append(tag2)
        await async_db_session.commit()

        # Get popular tags
        popular_tags = await search_service.get_popular_tags(db=async_db_session, limit=10)

        assert len(popular_tags) >= 2
        # popular tag should have higher count
        tag_counts = dict(popular_tags)
        if "popular" in tag_counts and "rare" in tag_counts:
            assert tag_counts["popular"] > tag_counts["rare"]

    @pytest.mark.asyncio
    async def test_get_recent_content(self, async_db_session, test_user):
        """Test getting recent content"""
        # Create content
        for i in range(3):
            await create_test_content(
                async_db_session,
                title=f"Recent Post {i}",
                body="Content",
                author_id=test_user.id,
                status=ContentStatus.PUBLISHED,
            )

        # Get recent published content
        results = await search_service.get_recent_content(db=async_db_session, status="published", limit=10)

        assert len(results) >= 3
        # Should be ordered by created_at desc (most recent first)
        if len(results) >= 2:
            assert results[0].created_at >= results[1].created_at

    @pytest.mark.asyncio
    async def test_search_with_multiple_filters(self, async_db_session, test_user):
        """Test search with multiple filters combined"""
        category = await create_test_category(async_db_session, name="Tech")
        tag = await create_test_tag(async_db_session, name="python")

        content = await create_test_content(
            async_db_session,
            title="Python Tutorial",
            body="Learn Python programming",
            author_id=test_user.id,
            category_id=category.id,
            status=ContentStatus.PUBLISHED,
        )
        content.tags.append(tag)
        await async_db_session.commit()

        # Search with multiple filters
        results, total = await search_service.search_content(
            db=async_db_session,
            query="python",
            category_id=category.id,
            tag_ids=[tag.id],
            status="published",
            author_id=test_user.id,
            limit=10,
            offset=0,
        )

        assert total >= 1
        assert any(c.id == content.id for c in results)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, async_db_session):
        """Test search returns empty results when no matches"""
        results, total = await search_service.search_content(
            db=async_db_session, query="ThisQueryShouldNotMatchAnything12345", limit=10, offset=0
        )

        assert total == 0
        assert len(results) == 0

    async def test_singleton_instance(self):
        """Test search_service singleton exists"""
        assert search_service is not None
        assert isinstance(search_service, SearchService)
