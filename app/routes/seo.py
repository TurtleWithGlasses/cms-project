"""
SEO Routes

Provides endpoints for sitemap.xml, RSS feeds, and robots.txt.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.seo_service import SEOService

router = APIRouter(tags=["SEO"])


def get_base_url(request: Request) -> str:
    """Extract base URL from request."""
    return str(request.base_url).rstrip("/")


@router.get("/sitemap.xml")
async def get_sitemap(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate XML sitemap for search engines.

    Includes all published content, categories, and static pages.
    """
    base_url = get_base_url(request)
    service = SEOService(db, base_url)

    sitemap_xml = await service.generate_sitemap()

    return Response(
        content=sitemap_xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/robots.txt")
async def get_robots_txt(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Generate robots.txt for search engine crawlers.

    Defines crawling rules and sitemap location.
    """
    base_url = get_base_url(request)
    service = SEOService(db, base_url)

    robots_txt = await service.generate_robots_txt()

    return Response(
        content=robots_txt,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/feed.xml")
async def get_rss_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Number of items in feed"),
    category: int | None = Query(None, description="Filter by category ID"),
) -> Response:
    """
    Generate RSS 2.0 feed for content syndication.

    Returns the most recent published content in RSS format.
    """
    base_url = get_base_url(request)
    service = SEOService(db, base_url)

    rss_xml = await service.generate_rss_feed(limit=limit, category_id=category)

    return Response(
        content=rss_xml,
        media_type="application/rss+xml",
        headers={
            "Cache-Control": "public, max-age=1800",
            "Content-Type": "application/rss+xml; charset=utf-8",
        },
    )


@router.get("/atom.xml")
async def get_atom_feed(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Number of items in feed"),
    category: int | None = Query(None, description="Filter by category ID"),
) -> Response:
    """
    Generate Atom feed for content syndication.

    Returns the most recent published content in Atom format.
    """
    base_url = get_base_url(request)
    service = SEOService(db, base_url)

    atom_xml = await service.generate_atom_feed(limit=limit, category_id=category)

    return Response(
        content=atom_xml,
        media_type="application/atom+xml",
        headers={
            "Cache-Control": "public, max-age=1800",
            "Content-Type": "application/atom+xml; charset=utf-8",
        },
    )


@router.get("/feed/category/{category_id}")
async def get_category_rss_feed(
    category_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Number of items in feed"),
) -> Response:
    """
    Generate RSS feed for a specific category.

    Returns published content from the specified category.
    """
    base_url = get_base_url(request)
    service = SEOService(db, base_url)

    rss_xml = await service.generate_rss_feed(limit=limit, category_id=category_id)

    return Response(
        content=rss_xml,
        media_type="application/rss+xml",
        headers={
            "Cache-Control": "public, max-age=1800",
            "Content-Type": "application/rss+xml; charset=utf-8",
        },
    )
