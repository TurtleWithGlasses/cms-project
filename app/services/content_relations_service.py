"""
Content Relations Service

Provides CRUD operations for content relationships, series, and redirects.
"""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Content
from app.models.content_relations import (
    ContentRedirect,
    ContentRelation,
    ContentSeries,
    ContentSeriesItem,
    RelationType,
)

logger = logging.getLogger(__name__)


class ContentRelationsService:
    """Service for managing content relationships, series, and redirects."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============== Content Relations ==============

    async def create_relation(
        self,
        source_content_id: int,
        target_content_id: int,
        relation_type: RelationType = RelationType.RELATED_TO,
        description: str | None = None,
        created_by_id: int | None = None,
    ) -> ContentRelation:
        """Create a relationship between two content items."""
        if source_content_id == target_content_id:
            raise ValueError("Content cannot be related to itself")

        source = await self.db.get(Content, source_content_id)
        if not source:
            raise ValueError(f"Source content with ID {source_content_id} not found")

        target = await self.db.get(Content, target_content_id)
        if not target:
            raise ValueError(f"Target content with ID {target_content_id} not found")

        existing = await self.db.execute(
            select(ContentRelation).where(
                ContentRelation.source_content_id == source_content_id,
                ContentRelation.target_content_id == target_content_id,
                ContentRelation.relation_type == relation_type,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("This relationship already exists")

        relation = ContentRelation(
            source_content_id=source_content_id,
            target_content_id=target_content_id,
            relation_type=relation_type,
            description=description,
            created_by_id=created_by_id,
        )
        self.db.add(relation)
        await self.db.commit()
        await self.db.refresh(relation)

        logger.info(
            "Created content relation: %d -> %d (%s)",
            source_content_id,
            target_content_id,
            relation_type.value,
        )
        return relation

    async def get_relations(
        self,
        content_id: int,
        relation_type: RelationType | None = None,
    ) -> list[ContentRelation]:
        """Get all relations for a content item (both directions)."""
        query = (
            select(ContentRelation)
            .options(
                selectinload(ContentRelation.source_content),
                selectinload(ContentRelation.target_content),
            )
            .where(
                or_(
                    ContentRelation.source_content_id == content_id,
                    ContentRelation.target_content_id == content_id,
                )
            )
        )
        if relation_type:
            query = query.where(ContentRelation.relation_type == relation_type)

        query = query.order_by(ContentRelation.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_relation(self, relation_id: int) -> bool:
        """Delete a content relation."""
        relation = await self.db.get(ContentRelation, relation_id)
        if not relation:
            return False
        await self.db.delete(relation)
        await self.db.commit()
        logger.info("Deleted content relation: id=%d", relation_id)
        return True

    # ============== Content Series ==============

    async def create_series(
        self,
        title: str,
        slug: str,
        description: str | None = None,
        created_by_id: int | None = None,
    ) -> ContentSeries:
        """Create a new content series."""
        existing = await self.db.execute(select(ContentSeries).where(ContentSeries.slug == slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Series with slug '{slug}' already exists")

        series = ContentSeries(
            title=title,
            slug=slug,
            description=description,
            created_by_id=created_by_id,
        )
        self.db.add(series)
        await self.db.commit()
        await self.db.refresh(series)
        logger.info("Created content series: %s", title)
        return series

    async def get_series(self, series_id: int) -> ContentSeries | None:
        """Get a series by ID with items loaded."""
        result = await self.db.execute(
            select(ContentSeries)
            .options(selectinload(ContentSeries.items).selectinload(ContentSeriesItem.content))
            .where(ContentSeries.id == series_id)
        )
        return result.scalar_one_or_none()

    async def list_series(
        self,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = True,
    ) -> list[ContentSeries]:
        """List all series."""
        query = select(ContentSeries)
        if active_only:
            query = query.where(ContentSeries.is_active.is_(True))
        query = query.order_by(ContentSeries.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_series(
        self,
        series_id: int,
        title: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> ContentSeries | None:
        """Update a series."""
        series = await self.db.get(ContentSeries, series_id)
        if not series:
            return None
        if title is not None:
            series.title = title
        if description is not None:
            series.description = description
        if is_active is not None:
            series.is_active = is_active
        await self.db.commit()
        await self.db.refresh(series)
        logger.info("Updated content series: id=%d", series_id)
        return series

    async def delete_series(self, series_id: int) -> bool:
        """Delete a series (cascade deletes items)."""
        series = await self.db.get(ContentSeries, series_id)
        if not series:
            return False
        await self.db.delete(series)
        await self.db.commit()
        logger.info("Deleted content series: id=%d", series_id)
        return True

    async def add_to_series(
        self,
        series_id: int,
        content_id: int,
        order: int | None = None,
    ) -> ContentSeriesItem:
        """Add content to a series."""
        series = await self.db.get(ContentSeries, series_id)
        if not series:
            raise ValueError(f"Series with ID {series_id} not found")

        content = await self.db.get(Content, content_id)
        if not content:
            raise ValueError(f"Content with ID {content_id} not found")

        existing = await self.db.execute(
            select(ContentSeriesItem).where(
                ContentSeriesItem.series_id == series_id,
                ContentSeriesItem.content_id == content_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Content is already in this series")

        if order is None:
            result = await self.db.execute(
                select(func.coalesce(func.max(ContentSeriesItem.order), -1) + 1).where(
                    ContentSeriesItem.series_id == series_id
                )
            )
            order = result.scalar()

        item = ContentSeriesItem(
            series_id=series_id,
            content_id=content_id,
            order=order,
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        logger.info("Added content %d to series %d at order %d", content_id, series_id, order)
        return item

    async def remove_from_series(self, series_id: int, content_id: int) -> bool:
        """Remove content from a series."""
        result = await self.db.execute(
            select(ContentSeriesItem).where(
                ContentSeriesItem.series_id == series_id,
                ContentSeriesItem.content_id == content_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return False
        await self.db.delete(item)
        await self.db.commit()
        logger.info("Removed content %d from series %d", content_id, series_id)
        return True

    async def reorder_series(self, series_id: int, content_ids: list[int]) -> bool:
        """Reorder items in a series. content_ids is the new order."""
        for idx, content_id in enumerate(content_ids):
            result = await self.db.execute(
                select(ContentSeriesItem).where(
                    ContentSeriesItem.series_id == series_id,
                    ContentSeriesItem.content_id == content_id,
                )
            )
            item = result.scalar_one_or_none()
            if item:
                item.order = idx
        await self.db.commit()
        logger.info("Reordered series %d", series_id)
        return True

    # ============== Content Redirects ==============

    async def create_redirect(
        self,
        old_slug: str,
        content_id: int,
        status_code: int = 301,
        created_by_id: int | None = None,
    ) -> ContentRedirect:
        """Create a URL redirect for an old slug."""
        content = await self.db.get(Content, content_id)
        if not content:
            raise ValueError(f"Content with ID {content_id} not found")

        active_content = await self.db.execute(select(Content).where(Content.slug == old_slug))
        if active_content.scalar_one_or_none():
            raise ValueError(f"Slug '{old_slug}' is currently used by active content")

        existing = await self.db.execute(select(ContentRedirect).where(ContentRedirect.old_slug == old_slug))
        if existing.scalar_one_or_none():
            raise ValueError(f"Redirect for slug '{old_slug}' already exists")

        redirect = ContentRedirect(
            old_slug=old_slug,
            content_id=content_id,
            status_code=status_code,
            created_by_id=created_by_id,
        )
        self.db.add(redirect)
        await self.db.commit()
        await self.db.refresh(redirect)
        logger.info("Created redirect: %s -> content %d", old_slug, content_id)
        return redirect

    async def resolve_redirect(self, slug: str) -> ContentRedirect | None:
        """Resolve a slug to a redirect, if one exists."""
        result = await self.db.execute(
            select(ContentRedirect)
            .options(selectinload(ContentRedirect.content))
            .where(ContentRedirect.old_slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_redirects(
        self,
        content_id: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ContentRedirect]:
        """List redirects, optionally filtered by content_id."""
        query = select(ContentRedirect).options(selectinload(ContentRedirect.content))
        if content_id:
            query = query.where(ContentRedirect.content_id == content_id)
        query = query.order_by(ContentRedirect.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_redirect(self, redirect_id: int) -> bool:
        """Delete a redirect."""
        redirect = await self.db.get(ContentRedirect, redirect_id)
        if not redirect:
            return False
        await self.db.delete(redirect)
        await self.db.commit()
        logger.info("Deleted redirect: id=%d", redirect_id)
        return True
