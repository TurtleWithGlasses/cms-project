import asyncio
import contextlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.auth import get_current_user, get_current_user_with_role
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.content import Content, ContentStatus
from app.models.content_version import ContentVersion
from app.models.user import User
from app.scheduler import schedule_content
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate
from app.schemas.content_version import ContentVersionOut
from app.services import content_service, content_version_service
from app.services.webhook_service import WebhookEventDispatcher
from app.services.websocket_manager import broadcast_content_event
from app.utils.activity_log import log_activity
from app.utils.cache import CacheManager, cache_manager
from app.utils.field_selector import FieldSelector
from app.utils.slugify import slugify

logging.basicConfig(
    level=logging.INFO,  # Set the desired log level (INFO, DEBUG, etc.)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter()


async def fetch_content_by_id(content_id: int, db: AsyncSession) -> Content:
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


def validate_content_status(content: Content, required_status: ContentStatus):
    if content.status != required_status:
        raise HTTPException(status_code=400, detail=f"Content must be in {required_status.value} status.")


@router.post("/", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    content: ContentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        slug = content.slug or slugify(content.title)

        # Create new content
        new_content = Content(
            title=content.title,
            body=content.body,
            slug=slug,
            description=content.description,
            status=ContentStatus.DRAFT,
            meta_title=content.meta_title,
            meta_description=content.meta_description,
            meta_keywords=content.meta_keywords,
            author_id=current_user.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_content)
        await db.commit()
        await db.refresh(new_content)

        if content.publish_at:
            schedule_content(new_content.id, content.publish_at)

        # Log activity using a separate session
        try:
            await log_activity(
                action="create_draft",
                user_id=current_user.id,
                content_id=new_content.id,
                description=f"User {current_user.username} created draft content with ID {new_content.id}.",
                details={
                    "title": new_content.title,
                    "slug": new_content.slug,
                    "status": new_content.status.value,
                },
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")

        # Invalidate content list cache
        await cache_manager.invalidate_content()

        # Broadcast WebSocket event
        try:
            await broadcast_content_event("content.created", new_content.id, new_content.title, current_user.id)
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        # Dispatch webhook event (fire-and-forget)
        with contextlib.suppress(Exception):
            asyncio.create_task(
                WebhookEventDispatcher(db).content_created(new_content.id, new_content.title, current_user.id)
            )

        return new_content

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create content: {str(e)}") from e


@router.patch("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: int,
    content: ContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch content with eager loading
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.author))  # Add all necessary relationships
        .where(Content.id == content_id)
    )
    existing_content = result.scalars().first()

    if not existing_content:
        raise HTTPException(status_code=404, detail="Content not found.")

    # Validate slug
    if content.slug:
        slug = content.slug
        result = await db.execute(select(Content).where(Content.slug == slug, Content.id != content_id))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")
        existing_content.slug = slug
    elif content.title:
        existing_content.slug = slugify(content.title)

    # Save current version before applying updates
    version = ContentVersion(
        content_id=existing_content.id,
        title=existing_content.title,
        body=existing_content.body,
        slug=existing_content.slug,
        editor_id=current_user.id,
    )
    db.add(version)

    # Update fields
    existing_content.title = content.title or existing_content.title
    existing_content.body = content.body or existing_content.body
    existing_content.meta_title = content.meta_title or existing_content.meta_title
    existing_content.meta_description = content.meta_description or existing_content.meta_description
    existing_content.meta_keywords = content.meta_keywords or existing_content.meta_keywords
    existing_content.updated_at = datetime.now(timezone.utc)

    try:
        # Commit updates
        await db.commit()
        await db.refresh(existing_content)

        # Log the activity
        try:
            await log_activity(
                action="update_content",
                user_id=existing_content.author_id,
                content_id=content_id,
                description=f"Content with ID {content_id} updated.",
                details={"updated_fields": list(content.dict(exclude_unset=True).keys())},
            )
        except Exception as log_error:
            logger.warning(f"Failed to log activity for updated content {content_id}: {log_error}")

        # Invalidate content cache
        await cache_manager.invalidate_content(content_id)

        # Broadcast WebSocket event
        try:
            await broadcast_content_event(
                "content.updated", content_id, existing_content.title, existing_content.author_id
            )
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        # Dispatch webhook event (fire-and-forget)
        with contextlib.suppress(Exception):
            asyncio.create_task(
                WebhookEventDispatcher(db).content_updated(
                    content_id, existing_content.title, existing_content.author_id
                )
            )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update content: {str(e)}") from e

    return existing_content


@router.patch("/{content_id}/submit", response_model=ContentResponse)
async def submit_for_approval(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(["editor", "admin"])),
):
    logger.debug(f"DB session at start: {db}")
    content = await fetch_content_by_id(content_id, db)
    validate_content_status(content, ContentStatus.DRAFT)

    content.status = ContentStatus.PENDING
    content.updated_at = datetime.now(timezone.utc)

    details = {
        "id": content.id,
        "title": content.title,
        "slug": content.slug,
        "status": content.status,
        "description": content.description,
    }

    try:
        # Log activity within the same session and transaction
        new_log = ActivityLog(
            action="content_submission",
            user_id=current_user.id,
            content_id=content.id,
            description=f"Content with ID {content.id} submitted for approval.",
            details=details,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(new_log)

        # Commit both the content update and the log
        await db.commit()
        logger.info(f"Content {content_id} submitted for approval by user {current_user.id}")
    except Exception as e:
        logger.error(f"Failed to submit content {content_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit content: {str(e)}") from e

    return content


@router.patch("/{content_id}/approve", response_model=ContentResponse)
async def approve_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(["admin"])),
):
    try:
        # Fetch content and validate its current status
        content = await fetch_content_by_id(content_id, db)
        validate_content_status(content, ContentStatus.PENDING)

        # Update content status and timestamps
        content.status = ContentStatus.PUBLISHED
        content.publish_date = datetime.now(timezone.utc)
        content.updated_at = datetime.now(timezone.utc)

        # Prepare details for logging
        details = {
            "id": content.id,
            "title": content.title,
            "slug": content.slug,
            "status": content.status.value,  # Ensure Enum values are serialized
            "description": content.description,
        }

        # Add the log entry to the same session
        new_log = ActivityLog(
            action="content_approval",
            user_id=current_user.id,
            content_id=content.id,
            description=f"Content with ID {content.id} approved and published.",
            details=details,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(new_log)

        await db.commit()

        await db.refresh(content)

        # Invalidate content cache
        await cache_manager.invalidate_content(content_id)

        # Broadcast WebSocket event
        try:
            await broadcast_content_event("content.published", content.id, content.title, current_user.id)
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast failed: {ws_err}")

        # Dispatch webhook event (fire-and-forget)
        with contextlib.suppress(Exception):
            asyncio.create_task(
                WebhookEventDispatcher(db).content_published(content.id, content.title, current_user.id)
            )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve content: {str(e)}") from e

    finally:
        # Ensure session cleanup
        await db.close()

    return content


@router.get("/{content_id}/versions", response_model=list[ContentVersionOut])
async def get_content_versions(content_id: int, db: AsyncSession = Depends(get_db)):
    return await content_version_service.get_versions(content_id, db)


@router.post("/{content_id}/rollback/{version_id}", response_model=ContentResponse)
async def rollback_content_version(
    content_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await content_version_service.rollback_to_version(content_id, version_id, db, current_user)


@router.get("/", response_model=list[ContentResponse])
async def get_all_content_route(
    skip: int = 0,
    limit: int = 10,
    status: str | None = None,
    category_id: int | None = None,
    author_id: int | None = None,
    fields: FieldSelector = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # Try cache first
    cache_key = f"{CacheManager.PREFIX_CONTENT}list:{skip}:{limit}:{status}:{category_id}:{author_id}"
    cached = await cache_manager.get(cache_key)
    if cached is not None:
        if fields.has_selection:
            return fields.apply(cached)
        return cached

    result = await content_service.get_all_content(
        db, skip=skip, limit=limit, status=status, category_id=category_id, author_id=author_id
    )

    # Cache the serialized result
    try:
        serializable = [ContentResponse.model_validate(c).model_dump(mode="json") for c in result]
        await cache_manager.set(cache_key, serializable, CacheManager.TTL_SHORT)
    except Exception as e:
        logger.debug(f"Failed to cache content list: {e}")

    if fields.has_selection:
        return fields.apply(result)
    return result


# Search Endpoints


@router.get("/search/", response_model=dict)
async def search_content_endpoint(
    query: str | None = None,
    category_id: int | None = None,
    tag_ids: str | None = None,  # Comma-separated tag IDs
    status: str | None = None,
    author_id: int | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Search for content with comprehensive filtering.

    - **query**: Search text (searches title, body, and slug)
    - **category_id**: Filter by category
    - **tag_ids**: Comma-separated tag IDs (e.g., "1,2,3")
    - **status**: Filter by status (draft, pending, published)
    - **author_id**: Filter by author
    - **sort_by**: Field to sort by (created_at, updated_at, title, publish_at)
    - **sort_order**: asc or desc
    - **limit**: Maximum results (1-100)
    - **offset**: Pagination offset
    """
    from app.services.search_service import search_service

    # Parse tag IDs from comma-separated string
    parsed_tag_ids = None
    if tag_ids:
        try:
            parsed_tag_ids = [int(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]
        except ValueError as err:
            raise HTTPException(
                status_code=400, detail="Invalid tag_ids format. Use comma-separated integers."
            ) from err

    # Validate limit
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")

    # Validate sort options
    valid_sort_fields = ["created_at", "updated_at", "title", "publish_at"]
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort_by. Must be one of: {', '.join(valid_sort_fields)}")

    if sort_order.lower() not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort_order. Must be 'asc' or 'desc'")

    # Perform search
    results, total = await search_service.search_content(
        db=db,
        query=query,
        category_id=category_id,
        tag_ids=parsed_tag_ids,
        status=status,
        author_id=author_id,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@router.get("/search/by-tags/", response_model=dict)
async def search_by_tags_endpoint(
    tag_names: str,  # Comma-separated tag names
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Search content by tag names.

    - **tag_names**: Comma-separated tag names (e.g., "python,tutorial,beginner")
    - **limit**: Maximum results (1-100)
    - **offset**: Pagination offset
    """
    from app.services.search_service import search_service

    if not tag_names:
        raise HTTPException(status_code=400, detail="tag_names parameter is required")

    # Parse tag names
    parsed_tag_names = [name.strip() for name in tag_names.split(",") if name.strip()]

    if not parsed_tag_names:
        raise HTTPException(status_code=400, detail="No valid tag names provided")

    # Perform search
    results, total = await search_service.search_by_tags(
        db=db,
        tag_names=parsed_tag_names,
        limit=limit,
        offset=offset,
    )

    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
        "searched_tags": parsed_tag_names,
    }


@router.get("/search/by-category/{category_name}", response_model=dict)
async def search_by_category_endpoint(
    category_name: str,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Search content by category name.

    - **category_name**: Name of the category
    - **limit**: Maximum results (1-100)
    - **offset**: Pagination offset
    """
    from app.services.search_service import search_service

    results, total = await search_service.search_by_category(
        db=db,
        category_name=category_name,
        limit=limit,
        offset=offset,
    )

    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
        "category": category_name,
    }


@router.get("/search/popular-tags/", response_model=list)
async def get_popular_tags_endpoint(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get most popular tags by usage count.

    - **limit**: Maximum number of tags to return
    """
    # Try cache first
    cache_key = f"cache:tags:popular:{limit}"
    cached = await cache_manager.get(cache_key)
    if cached is not None:
        return cached

    from app.services.search_service import search_service

    tags = await search_service.get_popular_tags(db=db, limit=limit)

    result = [{"name": name, "count": count} for name, count in tags]
    await cache_manager.set(cache_key, result, CacheManager.TTL_MEDIUM)
    return result


@router.get("/search/recent/", response_model=list[ContentResponse])
async def get_recent_content_endpoint(
    status: str = "published",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get most recent content.

    - **status**: Content status filter (default: published)
    - **limit**: Maximum number of results
    """
    from app.services.search_service import search_service

    return await search_service.get_recent_content(db=db, status=status, limit=limit)


@router.post("/{content_id}/views")
async def record_content_view(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a content view for analytics.

    This is a public endpoint. Deduplicates views within a 30-minute window
    per user/IP.
    """
    from app.services.analytics_service import analytics_service

    # Verify content exists
    content = await db.get(Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Extract client info
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")

    recorded = await analytics_service.record_content_view(
        db=db,
        content_id=content_id,
        user_id=None,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
    )

    return {"recorded": recorded, "content_id": content_id}
