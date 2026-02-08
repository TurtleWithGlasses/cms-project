"""
Tests for Search Service

Tests search functionality including full-text search, filtering, and pagination.
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from utils.mock_utils import create_test_category, create_test_content, create_test_tag

from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.search_query import SearchQuery
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


class TestFullTextSearch:
    """Test PostgreSQL full-text search functionality"""

    @pytest.fixture(autouse=True)
    async def create_search_trigger(self, async_db_session):
        """Create the search vector trigger for FTS tests"""
        await async_db_session.execute(
            text("""
                CREATE OR REPLACE FUNCTION content_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector :=
                        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'C') ||
                        setweight(to_tsvector('english', COALESCE(NEW.meta_keywords, '')), 'D');
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
        )
        await async_db_session.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'content_search_vector_trigger'
                    ) THEN
                        CREATE TRIGGER content_search_vector_trigger
                        BEFORE INSERT OR UPDATE OF title, body, description, meta_keywords
                        ON content
                        FOR EACH ROW
                        EXECUTE FUNCTION content_search_vector_update();
                    END IF;
                END;
                $$;
            """)
        )
        await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_fulltext_search_basic(self, async_db_session, test_user):
        """Test basic full-text search returns matching content"""
        await create_test_content(
            async_db_session,
            title="Advanced Python Programming",
            body="This is a comprehensive guide to Python",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )
        await create_test_content(
            async_db_session,
            title="JavaScript Basics",
            body="Learn JavaScript from scratch",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        result = await search_service.fulltext_search(db=async_db_session, query="python", limit=10, offset=0)

        assert result["total"] >= 1
        assert len(result["results"]) >= 1
        assert result["query"] == "python"
        assert result["results"][0]["relevance_score"] > 0

    @pytest.mark.asyncio
    async def test_fulltext_search_relevance_ordering(self, async_db_session, test_user):
        """Test that title matches rank higher than body matches"""
        # Title match (weight A)
        await create_test_content(
            async_db_session,
            title="Database Administration Guide",
            body="Some generic content about technology",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )
        # Body match only (weight C)
        await create_test_content(
            async_db_session,
            title="Generic Technology Article",
            body="This guide covers database administration and management",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        result = await search_service.fulltext_search(
            db=async_db_session, query="database administration", limit=10, offset=0
        )

        assert result["total"] >= 2
        if len(result["results"]) >= 2:
            assert result["results"][0]["relevance_score"] >= result["results"][1]["relevance_score"]

    @pytest.mark.asyncio
    async def test_fulltext_search_with_status_filter(self, async_db_session, test_user):
        """Test full-text search with status filter"""
        await create_test_content(
            async_db_session,
            title="Published Python Guide",
            body="Python content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )
        await create_test_content(
            async_db_session,
            title="Draft Python Guide",
            body="Python draft content",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )

        result = await search_service.fulltext_search(
            db=async_db_session, query="python guide", status="published", limit=10, offset=0
        )

        assert result["total"] >= 1
        for item in result["results"]:
            assert item["content"].status == ContentStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_fulltext_search_highlights(self, async_db_session, test_user):
        """Test that highlighted snippets are returned"""
        await create_test_content(
            async_db_session,
            title="Machine Learning Tutorial",
            body="This tutorial covers the basics of machine learning algorithms and techniques",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
            description="A beginner guide to machine learning",
        )

        result = await search_service.fulltext_search(
            db=async_db_session, query="machine learning", highlight=True, limit=10, offset=0
        )

        assert result["total"] >= 1
        first_result = result["results"][0]
        assert first_result["highlights"] is not None
        assert "title" in first_result["highlights"]
        assert "body" in first_result["highlights"]
        assert "<mark>" in first_result["highlights"]["title"]

    @pytest.mark.asyncio
    async def test_fulltext_search_no_results(self, async_db_session, test_user):
        """Test full-text search returns empty when no matches"""
        result = await search_service.fulltext_search(
            db=async_db_session, query="xyznonexistentterm", limit=10, offset=0
        )

        assert result["total"] == 0
        assert len(result["results"]) == 0
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_fulltext_search_with_category_filter(self, async_db_session, test_user):
        """Test full-text search filtered by category"""
        category = await create_test_category(async_db_session, name="Programming")

        await create_test_content(
            async_db_session,
            title="Python in Programming",
            body="Python programming content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
            category_id=category.id,
        )
        await create_test_content(
            async_db_session,
            title="Python Uncategorized",
            body="Python without category",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        result = await search_service.fulltext_search(
            db=async_db_session,
            query="python",
            category_id=category.id,
            limit=10,
            offset=0,
        )

        assert result["total"] >= 1
        for item in result["results"]:
            assert item["content"].category_id == category.id


class TestSearchFacets:
    """Test faceted search functionality"""

    @pytest.fixture(autouse=True)
    async def create_search_trigger(self, async_db_session):
        """Create the search vector trigger"""
        await async_db_session.execute(
            text("""
                CREATE OR REPLACE FUNCTION content_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector :=
                        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(NEW.body, '')), 'C') ||
                        setweight(to_tsvector('english', COALESCE(NEW.meta_keywords, '')), 'D');
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
        )
        await async_db_session.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'content_search_vector_trigger'
                    ) THEN
                        CREATE TRIGGER content_search_vector_trigger
                        BEFORE INSERT OR UPDATE OF title, body, description, meta_keywords
                        ON content
                        FOR EACH ROW
                        EXECUTE FUNCTION content_search_vector_update();
                    END IF;
                END;
                $$;
            """)
        )
        await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_get_facets_without_query(self, async_db_session, test_user):
        """Test getting facets without a search query"""
        category = await create_test_category(async_db_session, name="DevOps")
        await create_test_content(
            async_db_session,
            title="DevOps Guide",
            body="DevOps content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
            category_id=category.id,
        )

        facets = await search_service.get_facets(db=async_db_session)

        assert "categories" in facets
        assert "statuses" in facets
        assert "tags" in facets
        assert "authors" in facets
        assert len(facets["statuses"]) >= 1

    @pytest.mark.asyncio
    async def test_get_facets_with_query(self, async_db_session, test_user):
        """Test getting facets filtered by a search query"""
        category = await create_test_category(async_db_session, name="WebDev")
        await create_test_content(
            async_db_session,
            title="React Tutorial",
            body="React web development",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
            category_id=category.id,
        )
        await create_test_content(
            async_db_session,
            title="Database Design",
            body="Database normalization",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )

        facets = await search_service.get_facets(db=async_db_session, query="react")

        assert "statuses" in facets


class TestSearchSuggestions:
    """Test autocomplete suggestions"""

    @pytest.mark.asyncio
    async def test_get_suggestions_prefix(self, async_db_session, test_user):
        """Test getting suggestions matching a prefix"""
        await create_test_content(
            async_db_session,
            title="Python Programming Guide",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )
        await create_test_content(
            async_db_session,
            title="Python Data Science",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )
        await create_test_content(
            async_db_session,
            title="JavaScript Guide",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        suggestions = await search_service.get_suggestions(db=async_db_session, prefix="Pyth", limit=10)

        assert len(suggestions) >= 2
        for s in suggestions:
            assert s["title"].startswith("Python")

    @pytest.mark.asyncio
    async def test_get_suggestions_only_published(self, async_db_session, test_user):
        """Test that suggestions only return published content"""
        await create_test_content(
            async_db_session,
            title="Draft Article",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )
        await create_test_content(
            async_db_session,
            title="Draft Notes",
            body="Content",
            author_id=test_user.id,
            status=ContentStatus.PUBLISHED,
        )

        suggestions = await search_service.get_suggestions(db=async_db_session, prefix="Draft", limit=10)

        assert len(suggestions) == 1
        assert suggestions[0]["title"] == "Draft Notes"

    @pytest.mark.asyncio
    async def test_get_suggestions_empty(self, async_db_session):
        """Test suggestions with no matches returns empty"""
        suggestions = await search_service.get_suggestions(db=async_db_session, prefix="XYZNonexistent", limit=10)

        assert len(suggestions) == 0


class TestSearchAnalytics:
    """Test search analytics tracking"""

    @pytest.mark.asyncio
    async def test_track_search(self, async_db_session, test_user):
        """Test that search queries are tracked"""
        await search_service.track_search(
            db=async_db_session,
            query="python tutorial",
            results_count=5,
            execution_time_ms=15.5,
            user_id=test_user.id,
        )

        result = await async_db_session.execute(select(SearchQuery).where(SearchQuery.query == "python tutorial"))
        record = result.scalars().first()

        assert record is not None
        assert record.normalized_query == "python tutorial"
        assert record.results_count == 5
        assert record.execution_time_ms == 15.5
        assert record.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_search_analytics(self, async_db_session, test_user):
        """Test search analytics aggregation"""
        for i in range(5):
            await search_service.track_search(
                db=async_db_session,
                query=f"query {i}",
                results_count=i * 2,
                execution_time_ms=10.0 + i,
                user_id=test_user.id,
            )
        await search_service.track_search(
            db=async_db_session,
            query="no results query",
            results_count=0,
            execution_time_ms=5.0,
        )

        analytics = await search_service.get_search_analytics(db=async_db_session, days=30)

        assert analytics["total_searches"] >= 6
        assert analytics["unique_queries"] >= 6
        assert analytics["avg_results_count"] >= 0
        assert analytics["avg_execution_time_ms"] >= 0
        assert len(analytics["top_queries"]) >= 1
        assert len(analytics["zero_result_queries"]) >= 1
