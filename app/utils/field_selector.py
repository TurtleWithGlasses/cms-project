"""
Field Selection Utility

Provides sparse fieldset support for API responses via ``?fields=id,title,slug``.
Use as a FastAPI dependency on any list or detail endpoint.
"""

from __future__ import annotations

from typing import Any

from fastapi import Query


class FieldSelector:
    """
    FastAPI dependency for field selection.

    Usage::

        @router.get("/items")
        async def list_items(fields: FieldSelector = Depends()):
            items = await get_items(db)
            return fields.apply(items)
    """

    def __init__(
        self,
        fields: str | None = Query(
            default=None,
            description="Comma-separated list of fields to include (e.g. id,title,slug)",
        ),
    ):
        self.requested_fields: set[str] | None = None
        if fields:
            self.requested_fields = {f.strip() for f in fields.split(",") if f.strip()}

    @property
    def has_selection(self) -> bool:
        """Return True when the caller requested specific fields."""
        return self.requested_fields is not None

    def apply(self, data: Any) -> Any:
        """Filter response data to only include requested fields."""
        if self.requested_fields is None:
            return data
        if isinstance(data, list):
            return [self._filter_item(item) for item in data]
        return self._filter_item(data)

    def _filter_item(self, item: Any) -> dict:
        """Filter a single item to requested fields."""
        if isinstance(item, dict):
            return {k: v for k, v in item.items() if k in self.requested_fields}
        # Pydantic model
        if hasattr(item, "model_dump"):
            full = item.model_dump(mode="json")
            return {k: v for k, v in full.items() if k in self.requested_fields}
        # Plain object
        if hasattr(item, "__dict__"):
            full = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
            return {k: v for k, v in full.items() if k in self.requested_fields}
        return item
