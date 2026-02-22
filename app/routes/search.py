"""
Search Routes

API endpoints for full-text search, suggestions, facets, and search analytics.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_read_db
from app.models.user import User
from app.schemas.search import (
    FullTextSearchResponse,
    SearchAnalyticsResponse,
    SearchFacets,
    SearchSuggestionsResponse,
)
from app.services.search_service import search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=FullTextSearchResponse)
async def fulltext_search(
    q: str = Query(
        ...,
        min_length=2,
        max_length=200,
        description="Search query (supports AND, OR, NOT, quoted phrases)",
    ),
    category_id: int | None = None,
    tag_ids: str | None = Query(None, description="Comma-separated tag IDs"),
    content_status: str | None = Query(None, alias="status", description="Filter by content status"),
    author_id: int | None = None,
    date_from: datetime | None = Query(None, description="Filter content created after this date (ISO format)"),
    date_to: datetime | None = Query(None, description="Filter content created before this date (ISO format)"),
    sort_by: str = Query(
        "relevance",
        description="Sort by: relevance, created_at, updated_at, title",
    ),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    highlight: bool = Query(True, description="Include highlighted snippets"),
    db: AsyncSession = Depends(get_read_db),
):
    """
    Full-text search across all content using PostgreSQL tsvector.

    Supports natural language queries with AND, OR, NOT operators and quoted phrases.
    Results are ranked by relevance score with optional highlighted snippets.
    """
    # Validate sort options
    valid_sort_fields = ["relevance", "created_at", "updated_at", "title"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sort_fields)}",
        )

    if sort_order.lower() not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort_order. Must be 'asc' or 'desc'",
        )

    # Parse tag IDs
    parsed_tag_ids = None
    if tag_ids:
        try:
            parsed_tag_ids = [int(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tag_ids format. Use comma-separated integers.",
            ) from err

    result = await search_service.fulltext_search(
        db=db,
        query=q,
        category_id=category_id,
        tag_ids=parsed_tag_ids,
        status=content_status,
        author_id=author_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
        highlight=highlight,
    )

    return result


@router.get("/facets", response_model=SearchFacets)
async def get_search_facets(
    q: str | None = Query(
        None,
        description="Optional query to filter facets to matching content only",
    ),
    db: AsyncSession = Depends(get_read_db),
):
    """
    Get faceted search counts for categories, tags, statuses, and authors.

    If a query is provided, facets are scoped to content matching that query.
    Otherwise, facets reflect all content.
    """
    return await search_service.get_facets(db=db, query=q)


@router.get("/suggestions", response_model=SearchSuggestionsResponse)
async def get_search_suggestions(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search prefix for autocomplete",
    ),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_read_db),
):
    """
    Get autocomplete suggestions based on published content titles.
    """
    suggestions = await search_service.get_suggestions(db=db, prefix=q, limit=limit)

    return {"suggestions": suggestions, "query": q}


@router.get("/analytics", response_model=SearchAnalyticsResponse)
async def get_search_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
    db: AsyncSession = Depends(get_read_db),
):
    """
    Get search analytics data including top queries, zero-result queries,
    and search volume over time. Requires admin or superadmin role.
    """
    return await search_service.get_search_analytics(db=db, days=days)
