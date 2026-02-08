"""
Search Service

Provides full-text search functionality for content with filtering and pagination.
Includes PostgreSQL full-text search with relevance scoring, highlighting,
faceted search, autocomplete suggestions, and search analytics.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import settings
from app.models.category import Category
from app.models.content import Content
from app.models.content_tags import content_tags
from app.models.search_query import SearchQuery
from app.models.tag import Tag

logger = logging.getLogger(__name__)


class SearchService:
    """Service for searching content across the CMS"""

    # ========================================================================
    # Legacy search methods (backward compatibility)
    # ========================================================================

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
        stmt = stmt.order_by(sort_column.asc()) if sort_order.lower() == "asc" else stmt.order_by(sort_column.desc())

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

    # ========================================================================
    # Full-Text Search methods
    # ========================================================================

    @staticmethod
    async def fulltext_search(
        db: AsyncSession,
        query: str,
        category_id: int | None = None,
        tag_ids: list[int] | None = None,
        status: str | None = None,
        author_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        highlight: bool = True,
        user_id: int | None = None,
    ) -> dict:
        """
        Full-text search using PostgreSQL tsvector/tsquery with relevance scoring.

        Args:
            db: Database session
            query: Search query string
            category_id: Filter by category ID
            tag_ids: Filter by tag IDs
            status: Filter by content status
            author_id: Filter by author ID
            date_from: Filter by start date
            date_to: Filter by end date
            sort_by: Sort by (relevance, created_at, updated_at, title)
            sort_order: Sort order (asc, desc)
            limit: Maximum results
            offset: Pagination offset
            highlight: Whether to include highlighted snippets
            user_id: Current user ID for analytics

        Returns:
            dict matching FullTextSearchResponse schema
        """
        start_time = time.time()
        lang = settings.search_language
        hl_opts = (
            f"MaxWords={settings.search_highlight_max_words}, "
            f"MinWords={settings.search_highlight_min_words}, "
            "StartSel=<mark>, StopSel=</mark>"
        )

        # Build dynamic WHERE clause parts
        where_clauses = ["c.search_vector @@ query"]
        params: dict = {"q": query, "lang": lang, "hl_opts": hl_opts}

        if category_id is not None:
            where_clauses.append("c.category_id = :category_id")
            params["category_id"] = category_id

        if status:
            where_clauses.append("c.status = :status")
            params["status"] = status

        if author_id is not None:
            where_clauses.append("c.author_id = :author_id")
            params["author_id"] = author_id

        if date_from:
            where_clauses.append("c.created_at >= :date_from")
            params["date_from"] = date_from

        if date_to:
            where_clauses.append("c.created_at <= :date_to")
            params["date_to"] = date_to

        # Tag filter via subquery
        if tag_ids and len(tag_ids) > 0:
            tag_placeholders = ", ".join(f":tag_{i}" for i in range(len(tag_ids)))
            for i, tid in enumerate(tag_ids):
                params[f"tag_{i}"] = tid
            where_clauses.append(
                f"c.id IN (SELECT content_id FROM content_tags "  # nosec B608
                f"WHERE tag_id IN ({tag_placeholders}) "
                f"GROUP BY content_id "
                f"HAVING COUNT(tag_id) = :tag_count)"
            )
            params["tag_count"] = len(tag_ids)

        where_sql = " AND ".join(where_clauses)

        # Determine sort
        if sort_by == "relevance":
            order_sql = f"score {'DESC' if sort_order == 'desc' else 'ASC'}"
        elif sort_by == "title":
            order_sql = f"c.title {'DESC' if sort_order == 'desc' else 'ASC'}"
        elif sort_by == "updated_at":
            order_sql = f"c.updated_at {'DESC' if sort_order == 'desc' else 'ASC'}"
        else:
            order_sql = f"c.created_at {'DESC' if sort_order == 'desc' else 'ASC'}"

        # Count total matches
        count_sql = text(f"SELECT COUNT(*) FROM content c, websearch_to_tsquery(:lang, :q) AS query WHERE {where_sql}")  # nosec B608
        count_result = await db.execute(count_sql, params)
        total = count_result.scalar() or 0

        if total == 0:
            execution_time_ms = (time.time() - start_time) * 1000
            # Track analytics
            if settings.search_analytics_enabled:
                await SearchService.track_search(
                    db=db,
                    query=query,
                    results_count=0,
                    execution_time_ms=execution_time_ms,
                    user_id=user_id,
                )
            return {
                "results": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "has_more": False,
                "query": query,
                "facets": None,
                "execution_time_ms": round(execution_time_ms, 2),
            }

        # Build highlight columns
        highlight_cols = ""
        if highlight:
            highlight_cols = (
                ", ts_headline(:lang, c.title, query, :hl_opts) AS title_hl"
                ", ts_headline(:lang, c.body, query, :hl_opts) AS body_hl"
                ", ts_headline(:lang, COALESCE(c.description, ''), query, :hl_opts) AS desc_hl"
            )

        # Main search query
        search_sql = text(
            f"SELECT c.id, ts_rank(c.search_vector, query) AS score"  # nosec B608
            f"{highlight_cols} "
            f"FROM content c, websearch_to_tsquery(:lang, :q) AS query "
            f"WHERE {where_sql} "
            f"ORDER BY {order_sql} "
            f"LIMIT :lim OFFSET :off"
        )
        params["lim"] = limit
        params["off"] = offset

        search_result = await db.execute(search_sql, params)
        rows = search_result.all()

        if not rows:
            execution_time_ms = (time.time() - start_time) * 1000
            return {
                "results": [],
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total,
                "query": query,
                "facets": None,
                "execution_time_ms": round(execution_time_ms, 2),
            }

        # Extract IDs and metadata
        ids = [row[0] for row in rows]
        scores = {row[0]: row[1] for row in rows}
        highlights_map = {}
        if highlight:
            for row in rows:
                highlights_map[row[0]] = {
                    "title": row[2],
                    "body": row[3],
                    "description": row[4],
                }

        # Load full Content objects with relationships
        content_stmt = (
            select(Content)
            .where(Content.id.in_(ids))
            .options(
                joinedload(Content.author),
                joinedload(Content.category),
                joinedload(Content.tags),
            )
        )
        content_result = await db.execute(content_stmt)
        content_objects = {c.id: c for c in content_result.unique().scalars().all()}

        # Build ordered results
        results = []
        for cid in ids:
            content = content_objects.get(cid)
            if content:
                results.append(
                    {
                        "content": content,
                        "relevance_score": round(float(scores.get(cid, 0)), 6),
                        "highlights": highlights_map.get(cid) if highlight else None,
                    }
                )

        execution_time_ms = (time.time() - start_time) * 1000

        # Track analytics
        if settings.search_analytics_enabled:
            await SearchService.track_search(
                db=db,
                query=query,
                results_count=total,
                execution_time_ms=execution_time_ms,
                user_id=user_id,
                filters_used={
                    k: v
                    for k, v in {
                        "category_id": category_id,
                        "tag_ids": tag_ids,
                        "status": status,
                        "author_id": author_id,
                        "date_from": str(date_from) if date_from else None,
                        "date_to": str(date_to) if date_to else None,
                    }.items()
                    if v is not None
                }
                or None,
            )

        return {
            "results": results,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
            "query": query,
            "facets": None,
            "execution_time_ms": round(execution_time_ms, 2),
        }

    @staticmethod
    async def get_facets(
        db: AsyncSession,
        query: str | None = None,
    ) -> dict:
        """
        Get faceted search counts for categories, tags, statuses, and authors.

        Args:
            db: Database session
            query: Optional search query to filter facets

        Returns:
            dict matching SearchFacets schema
        """
        lang = settings.search_language

        # Build optional FTS filter
        fts_join = ""
        fts_where = ""
        params: dict = {}
        if query:
            fts_join = f", websearch_to_tsquery('{lang}', :q) AS query"
            fts_where = " AND c.search_vector @@ query"
            params["q"] = query

        # Category facets
        cat_sql = text(
            f"SELECT c.category_id, cat.name, COUNT(*) as cnt "  # nosec B608
            f"FROM content c{fts_join} "
            f"LEFT JOIN categories cat ON c.category_id = cat.id "
            f"WHERE c.category_id IS NOT NULL{fts_where} "
            f"GROUP BY c.category_id, cat.name "
            f"ORDER BY cnt DESC LIMIT 20"
        )
        cat_result = await db.execute(cat_sql, params)
        categories = [{"value": str(row[0]), "label": row[1] or "Unknown", "count": row[2]} for row in cat_result.all()]

        # Status facets
        status_sql = text(
            f"SELECT c.status, COUNT(*) as cnt "  # nosec B608
            f"FROM content c{fts_join} "
            f"WHERE 1=1{fts_where} "
            f"GROUP BY c.status "
            f"ORDER BY cnt DESC"
        )
        status_result = await db.execute(status_sql, params)
        statuses = [{"value": row[0], "label": row[0].title(), "count": row[1]} for row in status_result.all()]

        # Tag facets
        tag_sql = text(
            f"SELECT t.id, t.name, COUNT(*) as cnt "  # nosec B608
            f"FROM content c{fts_join} "
            f"JOIN content_tags ct ON c.id = ct.content_id "
            f"JOIN tags t ON ct.tag_id = t.id "
            f"WHERE 1=1{fts_where} "
            f"GROUP BY t.id, t.name "
            f"ORDER BY cnt DESC LIMIT 20"
        )
        tag_result = await db.execute(tag_sql, params)
        tags = [{"value": str(row[0]), "label": row[1], "count": row[2]} for row in tag_result.all()]

        # Author facets
        author_sql = text(
            f"SELECT c.author_id, u.username, COUNT(*) as cnt "  # nosec B608
            f"FROM content c{fts_join} "
            f"JOIN users u ON c.author_id = u.id "
            f"WHERE 1=1{fts_where} "
            f"GROUP BY c.author_id, u.username "
            f"ORDER BY cnt DESC LIMIT 20"
        )
        author_result = await db.execute(author_sql, params)
        authors = [{"value": str(row[0]), "label": row[1], "count": row[2]} for row in author_result.all()]

        return {
            "categories": categories,
            "tags": tags,
            "statuses": statuses,
            "authors": authors,
        }

    @staticmethod
    async def get_suggestions(
        db: AsyncSession,
        prefix: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get autocomplete suggestions based on content title prefix.

        Args:
            db: Database session
            prefix: Query prefix string
            limit: Maximum suggestions

        Returns:
            List of suggestion dicts with id, title, slug
        """
        stmt = (
            select(Content.id, Content.title, Content.slug)
            .where(
                Content.title.ilike(f"{prefix}%"),
                Content.status == "published",
            )
            .order_by(Content.title)
            .limit(limit)
        )

        result = await db.execute(stmt)
        return [{"id": row[0], "title": row[1], "slug": row[2]} for row in result.all()]

    # ========================================================================
    # Search Analytics
    # ========================================================================

    @staticmethod
    async def track_search(
        db: AsyncSession,
        query: str,
        results_count: int,
        execution_time_ms: float,
        user_id: int | None = None,
        filters_used: dict | None = None,
    ) -> None:
        """
        Track a search query for analytics.

        Args:
            db: Database session
            query: The search query
            results_count: Number of results found
            execution_time_ms: Execution time in ms
            user_id: User who performed the search
            filters_used: Filters applied to the search
        """
        try:
            search_record = SearchQuery(
                query=query,
                normalized_query=query.strip().lower(),
                results_count=results_count,
                user_id=user_id,
                filters_used=filters_used,
                execution_time_ms=round(execution_time_ms, 2),
            )
            db.add(search_record)
            await db.commit()
        except Exception:
            logger.warning("Failed to track search query", exc_info=True)
            await db.rollback()

    @staticmethod
    async def get_search_analytics(
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """
        Get search analytics for the specified period.

        Args:
            db: Database session
            days: Number of days to analyze

        Returns:
            dict matching SearchAnalyticsResponse schema
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total searches
        total_result = await db.execute(select(func.count(SearchQuery.id)).where(SearchQuery.created_at >= since))
        total_searches = total_result.scalar() or 0

        # Unique queries
        unique_result = await db.execute(
            select(func.count(func.distinct(SearchQuery.normalized_query))).where(SearchQuery.created_at >= since)
        )
        unique_queries = unique_result.scalar() or 0

        # Average results count
        avg_results_result = await db.execute(
            select(func.avg(SearchQuery.results_count)).where(SearchQuery.created_at >= since)
        )
        avg_results_count = float(avg_results_result.scalar() or 0)

        # Average execution time
        avg_time_result = await db.execute(
            select(func.avg(SearchQuery.execution_time_ms)).where(SearchQuery.created_at >= since)
        )
        avg_execution_time_ms = float(avg_time_result.scalar() or 0)

        # Top queries
        top_queries_result = await db.execute(
            select(
                SearchQuery.normalized_query,
                func.count(SearchQuery.id).label("count"),
                func.avg(SearchQuery.results_count).label("avg_results"),
            )
            .where(SearchQuery.created_at >= since)
            .group_by(SearchQuery.normalized_query)
            .order_by(func.count(SearchQuery.id).desc())
            .limit(20)
        )
        top_queries = [
            {
                "query": row[0],
                "count": row[1],
                "avg_results": round(float(row[2] or 0), 1),
            }
            for row in top_queries_result.all()
        ]

        # Zero-result queries
        zero_result = await db.execute(
            select(
                SearchQuery.normalized_query,
                func.count(SearchQuery.id).label("count"),
            )
            .where(
                SearchQuery.created_at >= since,
                SearchQuery.results_count == 0,
            )
            .group_by(SearchQuery.normalized_query)
            .order_by(func.count(SearchQuery.id).desc())
            .limit(10)
        )
        zero_result_queries = [{"query": row[0], "count": row[1]} for row in zero_result.all()]

        # Searches over time (per day)
        daily_result = await db.execute(
            text(
                "SELECT DATE(created_at) as day, COUNT(*) as count "
                "FROM search_queries "
                "WHERE created_at >= :since "
                "GROUP BY DATE(created_at) "
                "ORDER BY day"
            ),
            {"since": since},
        )
        searches_over_time = [{"date": str(row[0]), "count": row[1]} for row in daily_result.all()]

        return {
            "total_searches": total_searches,
            "unique_queries": unique_queries,
            "avg_results_count": round(avg_results_count, 1),
            "avg_execution_time_ms": round(avg_execution_time_ms, 2),
            "top_queries": top_queries,
            "zero_result_queries": zero_result_queries,
            "searches_over_time": searches_over_time,
        }


# Singleton instance
search_service = SearchService()
