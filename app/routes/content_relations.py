"""
Content Relations Routes

API endpoints for content relationships, series/collections, and URL redirects.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.content_relations import RelationType
from app.models.user import User
from app.services.content_relations_service import ContentRelationsService

router = APIRouter()


# ============== Schemas ==============


class ContentBrief(BaseModel):
    """Brief content info for relationship responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    status: str


class RelationCreate(BaseModel):
    target_content_id: int
    relation_type: RelationType = RelationType.RELATED_TO
    description: str | None = None


class RelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_content_id: int
    target_content_id: int
    relation_type: RelationType
    description: str | None
    created_at: datetime
    source_content: ContentBrief | None = None
    target_content: ContentBrief | None = None


class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class SeriesUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class SeriesItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_id: int
    order: int
    added_at: datetime
    content: ContentBrief | None = None


class SeriesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[SeriesItemResponse] = []


class AddToSeriesRequest(BaseModel):
    content_id: int
    order: int | None = None


class ReorderSeriesRequest(BaseModel):
    content_ids: list[int]


class RedirectCreate(BaseModel):
    old_slug: str = Field(..., min_length=1, max_length=255)
    content_id: int
    status_code: int = Field(301, ge=301, le=302)


class RedirectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    old_slug: str
    content_id: int
    status_code: int
    created_at: datetime
    content: ContentBrief | None = None


# ============== Helpers ==============


def _content_brief(content) -> ContentBrief | None:
    if not content:
        return None
    return ContentBrief(
        id=content.id,
        title=content.title,
        slug=content.slug,
        status=content.status.value if hasattr(content.status, "value") else content.status,
    )


def _relation_resp(r) -> RelationResponse:
    return RelationResponse(
        id=r.id,
        source_content_id=r.source_content_id,
        target_content_id=r.target_content_id,
        relation_type=r.relation_type,
        description=r.description,
        created_at=r.created_at,
        source_content=_content_brief(getattr(r, "source_content", None)),
        target_content=_content_brief(getattr(r, "target_content", None)),
    )


def _series_item_resp(item) -> SeriesItemResponse:
    return SeriesItemResponse(
        id=item.id,
        content_id=item.content_id,
        order=item.order,
        added_at=item.added_at,
        content=_content_brief(getattr(item, "content", None)),
    )


def _series_resp(s) -> SeriesResponse:
    items = []
    if hasattr(s, "items") and s.items:
        items = [_series_item_resp(i) for i in s.items]
    return SeriesResponse(
        id=s.id,
        title=s.title,
        slug=s.slug,
        description=s.description,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at,
        items=items,
    )


def _redirect_resp(r) -> RedirectResponse:
    return RedirectResponse(
        id=r.id,
        old_slug=r.old_slug,
        content_id=r.content_id,
        status_code=r.status_code,
        created_at=r.created_at,
        content=_content_brief(getattr(r, "content", None)),
    )


# ============== Content Relations Endpoints ==============


@router.get("/content/{content_id}/relations", response_model=list[RelationResponse])
async def get_content_relations(
    content_id: int,
    relation_type: RelationType | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all relations for a content item."""
    service = ContentRelationsService(db)
    relations = await service.get_relations(content_id, relation_type)
    return [_relation_resp(r) for r in relations]


@router.post(
    "/content/{content_id}/relations",
    response_model=RelationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_relation(
    content_id: int,
    data: RelationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a relationship between two content items."""
    service = ContentRelationsService(db)
    try:
        relation = await service.create_relation(
            source_content_id=content_id,
            target_content_id=data.target_content_id,
            relation_type=data.relation_type,
            description=data.description,
            created_by_id=current_user.id,
        )
        return _relation_resp(relation)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.delete("/relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content_relation(
    relation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a content relation."""
    service = ContentRelationsService(db)
    if not await service.delete_relation(relation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relation not found")


# ============== Series Endpoints ==============


@router.get("/series", response_model=list[SeriesResponse])
async def list_series(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all content series."""
    service = ContentRelationsService(db)
    skip = (page - 1) * limit
    series_list = await service.list_series(skip=skip, limit=limit, active_only=active_only)
    return [_series_resp(s) for s in series_list]


@router.post("/series", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    data: SeriesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new content series (editor+ required)."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editor or admin privileges required")
    service = ContentRelationsService(db)
    try:
        series = await service.create_series(
            title=data.title,
            slug=data.slug,
            description=data.description,
            created_by_id=current_user.id,
        )
        return _series_resp(series)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/series/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a content series by ID with its items."""
    service = ContentRelationsService(db)
    series = await service.get_series(series_id)
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
    return _series_resp(series)


@router.put("/series/{series_id}", response_model=SeriesResponse)
async def update_series(
    series_id: int,
    data: SeriesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a content series (editor+ required)."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editor or admin privileges required")
    service = ContentRelationsService(db)
    series = await service.update_series(
        series_id=series_id,
        title=data.title,
        description=data.description,
        is_active=data.is_active,
    )
    if not series:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
    series = await service.get_series(series_id)
    return _series_resp(series)


@router.delete("/series/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a content series (admin+ required)."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    service = ContentRelationsService(db)
    if not await service.delete_series(series_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")


@router.post(
    "/series/{series_id}/items",
    response_model=SeriesItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_series(
    series_id: int,
    data: AddToSeriesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add content to a series."""
    service = ContentRelationsService(db)
    try:
        item = await service.add_to_series(
            series_id=series_id,
            content_id=data.content_id,
            order=data.order,
        )
        return _series_item_resp(item)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.delete("/series/{series_id}/items/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_series(
    series_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove content from a series."""
    service = ContentRelationsService(db)
    if not await service.remove_from_series(series_id, content_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found in this series")


@router.put("/series/{series_id}/reorder")
async def reorder_series(
    series_id: int,
    data: ReorderSeriesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reorder items in a series."""
    service = ContentRelationsService(db)
    await service.reorder_series(series_id=series_id, content_ids=data.content_ids)
    return {"message": "Series reordered successfully"}


# ============== Redirect Endpoints ==============


@router.get("/redirects", response_model=list[RedirectResponse])
async def list_redirects(
    content_id: int | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all URL redirects."""
    service = ContentRelationsService(db)
    skip = (page - 1) * limit
    redirects = await service.list_redirects(content_id=content_id, skip=skip, limit=limit)
    return [_redirect_resp(r) for r in redirects]


@router.post("/redirects", response_model=RedirectResponse, status_code=status.HTTP_201_CREATED)
async def create_redirect(
    data: RedirectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a URL redirect (editor+ required)."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin", "editor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editor or admin privileges required")
    service = ContentRelationsService(db)
    try:
        redirect = await service.create_redirect(
            old_slug=data.old_slug,
            content_id=data.content_id,
            status_code=data.status_code,
            created_by_id=current_user.id,
        )
        return _redirect_resp(redirect)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/redirects/resolve/{slug}")
async def resolve_redirect(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Resolve a slug to its redirect target (public endpoint)."""
    service = ContentRelationsService(db)
    redirect = await service.resolve_redirect(slug)
    if not redirect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No redirect found for this slug")
    return {
        "old_slug": redirect.old_slug,
        "new_slug": redirect.content.slug if redirect.content else None,
        "content_id": redirect.content_id,
        "status_code": redirect.status_code,
    }


@router.delete("/redirects/{redirect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_redirect(
    redirect_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a URL redirect (admin+ required)."""
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    service = ContentRelationsService(db)
    if not await service.delete_redirect(redirect_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redirect not found")
