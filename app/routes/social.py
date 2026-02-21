"""Social sharing endpoints — share URLs, Open Graph/Twitter Card metadata."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.content import Content, ContentStatus
from app.services.seo_service import SEOService
from app.services.social_service import SocialSharingService

router = APIRouter(tags=["Social"])


@router.get("/social/content/{content_id}/share")
async def get_share_urls(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return social sharing URLs and Open Graph/Twitter Card metadata for a content item."""
    result = await db.execute(
        select(Content)
        .where(Content.id == content_id, Content.status == ContentStatus.PUBLISHED)
        .options(selectinload(Content.author), selectinload(Content.category))
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found") from None

    base_url = str(request.base_url).rstrip("/")
    sharing = SocialSharingService()
    seo = SEOService(db, base_url)

    return {
        "urls": sharing.get_share_urls(content, base_url),
        "meta": seo.get_content_og_tags(content, base_url),
    }


@router.get("/social/content/{content_id}/meta")
async def get_content_meta(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return full SEO metadata: canonical URL, OG tags, Twitter card, and JSON-LD."""
    result = await db.execute(
        select(Content)
        .where(Content.id == content_id, Content.status == ContentStatus.PUBLISHED)
        .options(selectinload(Content.author), selectinload(Content.category))
    )
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found") from None

    base_url = str(request.base_url).rstrip("/")
    seo = SEOService(db, base_url)

    return {
        "canonical": f"{base_url}/content/{content.slug}",
        "og": seo.get_content_og_tags(content, base_url),
        "json_ld": seo.generate_article_json_ld(content, base_url),
        "website_json_ld": seo.generate_website_json_ld(base_url),
    }
