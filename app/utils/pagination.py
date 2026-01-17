"""
Pagination Utilities

Provides efficient pagination strategies including cursor-based pagination
for improved performance on large datasets.
"""

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar

from fastapi import HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CursorInfo:
    """Represents decoded cursor information"""

    id: int
    created_at: datetime | None = None
    sort_value: Any = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response model"""

    items: list[Any]
    total: int
    has_next: bool
    has_previous: bool
    next_cursor: str | None = None
    prev_cursor: str | None = None


def encode_cursor(item_id: int, created_at: datetime | None = None, sort_value: Any = None) -> str:
    """
    Encode pagination cursor.

    Args:
        item_id: The ID of the item
        created_at: Optional created_at timestamp
        sort_value: Optional additional sort value

    Returns:
        Base64 encoded cursor string
    """
    cursor_data = {"id": item_id}

    if created_at:
        cursor_data["created_at"] = created_at.isoformat()

    if sort_value is not None:
        cursor_data["sort_value"] = str(sort_value)

    json_str = json.dumps(cursor_data)
    return base64.urlsafe_b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> CursorInfo:
    """
    Decode pagination cursor.

    Args:
        cursor: Base64 encoded cursor string

    Returns:
        CursorInfo with decoded values

    Raises:
        HTTPException if cursor is invalid
    """
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)

        created_at = None
        if "created_at" in data:
            created_at = datetime.fromisoformat(data["created_at"])

        return CursorInfo(
            id=data["id"],
            created_at=created_at,
            sort_value=data.get("sort_value"),
        )
    except Exception as e:
        logger.warning(f"Invalid cursor: {e}")
        raise HTTPException(status_code=400, detail="Invalid pagination cursor") from e


async def paginate_with_cursor(
    db: AsyncSession,
    model,
    limit: int = 20,
    cursor: str | None = None,
    sort_column=None,
    sort_order: str = "desc",
    filters: list = None,
    options: list = None,
) -> tuple[list, str | None, bool]:
    """
    Perform cursor-based pagination on a model.

    Args:
        db: Database session
        model: SQLAlchemy model class
        limit: Number of items to return
        cursor: Optional cursor from previous request
        sort_column: Column to sort by (default: model.id)
        sort_order: "asc" or "desc"
        filters: Optional list of filter conditions
        options: Optional query options (eager loading, etc.)

    Returns:
        Tuple of (items, next_cursor, has_more)
    """
    # Default to sorting by id
    if sort_column is None:
        sort_column = model.id

    # Build base query
    query = select(model)

    # Apply options (eager loading)
    if options:
        for opt in options:
            query = query.options(opt)

    # Apply filters
    if filters:
        for f in filters:
            query = query.where(f)

    # Apply cursor condition
    if cursor:
        cursor_info = decode_cursor(cursor)

        # For descending order, get items with smaller id/sort_value
        if sort_order == "desc":
            if hasattr(model, "created_at") and cursor_info.created_at:
                query = query.where(
                    or_(
                        sort_column < cursor_info.created_at,
                        and_(sort_column == cursor_info.created_at, model.id < cursor_info.id),
                    )
                )
            else:
                query = query.where(model.id < cursor_info.id)
        else:
            # For ascending order, get items with larger id/sort_value
            if hasattr(model, "created_at") and cursor_info.created_at:
                query = query.where(
                    or_(
                        sort_column > cursor_info.created_at,
                        and_(sort_column == cursor_info.created_at, model.id > cursor_info.id),
                    )
                )
            else:
                query = query.where(model.id > cursor_info.id)

    # Apply sorting
    order_func = desc if sort_order == "desc" else asc
    if hasattr(model, "created_at"):
        query = query.order_by(order_func(sort_column), order_func(model.id))
    else:
        query = query.order_by(order_func(model.id))

    # Fetch one extra to check if there are more items
    query = query.limit(limit + 1)

    result = await db.execute(query)
    items = list(result.scalars().all())

    # Check if there are more items
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]  # Remove the extra item

    # Generate next cursor
    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        created_at = getattr(last_item, "created_at", None)
        next_cursor = encode_cursor(last_item.id, created_at)

    return items, next_cursor, has_more


async def get_total_count(db: AsyncSession, model, filters: list = None) -> int:
    """
    Get total count of items matching filters.

    Args:
        db: Database session
        model: SQLAlchemy model class
        filters: Optional list of filter conditions

    Returns:
        Total count
    """
    query = select(func.count(model.id))

    if filters:
        for f in filters:
            query = query.where(f)

    result = await db.execute(query)
    return result.scalar() or 0


class PaginationParams:
    """
    FastAPI dependency for pagination parameters.

    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends()):
            ...
    """

    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100, description="Number of items to return"),
        cursor: str | None = Query(default=None, description="Pagination cursor from previous request"),
        sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order"),
    ):
        self.limit = limit
        self.cursor = cursor
        self.sort_order = sort_order
