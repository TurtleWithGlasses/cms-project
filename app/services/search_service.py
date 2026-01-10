"""
Search Service

Provides full-text search functionality for content with filtering and pagination.
"""

from sqlalchemy import and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.models.category import Category
from app.models.content import Content
from app.models.content_tags import content_tags
from app.models.tag import Tag


class SearchService:
    """Service for searching content across the CMS"""

    @staticmethod
    async def search_content(
        db: AsyncSession,
        query: str | None = None,
        category_id: int | None = None,
        tag_ids: list[int] | None = None,
        status: str | None = None,
        author_id: int | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Content], int]:
        """
        Search for content with comprehensive filtering.

        Args:
            db: Database session
            query: Search query string (searches title and body)
            category_id: Filter by category ID
            tag_ids: Filter by tag IDs (content must have all specified tags)
            status: Filter by status (draft, pending, published)
            author_id: Filter by author user ID
            sort_by: Field to sort by (created_at, updated_at, title, publish_at)
            sort_order: Sort order (asc, desc)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            tuple: (list of Content objects, total count)
        """
        # Base query with eager loading
        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )

        # Build filters
        filters = []

        # Text search (case-insensitive)
        if query:
            search_filter = or_(
                func.lower(Content.title).contains(query.lower()),
                func.lower(Content.body).contains(query.lower()),
                func.lower(Content.slug).contains(query.lower()),
            )
            filters.append(search_filter)

        # Category filter
        if category_id is not None:
            filters.append(Content.category_id == category_id)

        # Status filter
        if status:
            filters.append(Content.status == status)

        # Author filter
        if author_id is not None:
            filters.append(Content.author_id == author_id)

        # Tag filters
        if tag_ids and len(tag_ids) > 0:
            # Content must have ALL specified tags
            tag_subquery = (
                select(content_tags.c.content_id)
                .where(content_tags.c.tag_id.in_(tag_ids))
                .group_by(content_tags.c.content_id)
                .having(func.count(content_tags.c.tag_id) == len(tag_ids))
            )
            filters.append(Content.id.in_(tag_subquery))

        # Apply all filters
        if filters:
            stmt = stmt.where(and_(*filters))

        # Count total results (before pagination)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count_result = await db.execute(count_stmt)
        total_count = total_count_result.scalar()

        # Sorting
        sort_column = getattr(Content, sort_by, Content.created_at)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        # Pagination
        stmt = stmt.limit(limit).offset(offset)

        # Execute query
        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        return list(content_list), total_count or 0

    @staticmethod
    async def search_by_tags(
        db: AsyncSession,
        tag_names: list[str],
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Content], int]:
        """
        Search content by tag names (content must have at least one tag).

        Args:
            db: Database session
            tag_names: List of tag names to search for
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            tuple: (list of Content objects, total count)
        """
        # Get tag IDs from names
        tag_result = await db.execute(
            select(Tag.id).where(func.lower(Tag.name).in_([name.lower() for name in tag_names]))
        )
        tag_ids = [row[0] for row in tag_result.all()]

        if not tag_ids:
            return [], 0

        # Find content with any of these tags
        stmt = (
            select(Content)
            .join(content_tags)
            .where(content_tags.c.tag_id.in_(tag_ids))
            .options(
                joinedload(Content.author),
                joinedload(Content.category),
                joinedload(Content.tags),
            )
            .distinct()
        )

        # Count total
        count_stmt = (
            select(func.count(Content.id.distinct()))
            .select_from(Content)
            .join(content_tags)
            .where(content_tags.c.tag_id.in_(tag_ids))
        )
        total_count_result = await db.execute(count_stmt)
        total_count = total_count_result.scalar()

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        # Execute
        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        return list(content_list), total_count or 0

    @staticmethod
    async def search_by_category(
        db: AsyncSession,
        category_name: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Content], int]:
        """
        Search content by category name.

        Args:
            db: Database session
            category_name: Category name to search for
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            tuple: (list of Content objects, total count)
        """
        # Get category ID
        category_result = await db.execute(
            select(Category.id).where(func.lower(Category.name) == category_name.lower())
        )
        category_id = category_result.scalar()

        if not category_id:
            return [], 0

        return await SearchService.search_content(
            db=db,
            category_id=category_id,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_popular_tags(
        db: AsyncSession,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        """
        Get most popular tags by usage count.

        Args:
            db: Database session
            limit: Maximum number of tags to return

        Returns:
            List of tuples (tag_name, usage_count)
        """
        stmt = (
            select(Tag.name, func.count(content_tags.c.content_id).label("usage_count"))
            .join(content_tags)
            .group_by(Tag.id, Tag.name)
            .order_by(func.count(content_tags.c.content_id).desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    @staticmethod
    async def get_recent_content(
        db: AsyncSession,
        status: str = "published",
        limit: int = 10,
    ) -> list[Content]:
        """
        Get most recent content.

        Args:
            db: Database session
            status: Content status filter
            limit: Maximum number of results

        Returns:
            List of Content objects
        """
        stmt = (
            select(Content)
            .where(Content.status == status)
            .options(
                joinedload(Content.author),
                joinedload(Content.category),
                joinedload(Content.tags),
            )
            .order_by(Content.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.unique().scalars().all())


# Singleton instance
search_service = SearchService()
