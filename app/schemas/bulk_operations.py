"""
Bulk Operations Schemas

Pydantic models for bulk operation requests and responses.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BulkContentPublishRequest(BaseModel):
    """Request to bulk publish content"""

    content_ids: list[int] = Field(..., min_length=1, description="List of content IDs to publish")


class BulkContentStatusUpdateRequest(BaseModel):
    """Request to bulk update content status"""

    content_ids: list[int] = Field(..., min_length=1, description="List of content IDs")
    status: str = Field(..., description="New status (draft, pending, published)")


class BulkContentDeleteRequest(BaseModel):
    """Request to bulk delete content"""

    content_ids: list[int] = Field(..., min_length=1, description="List of content IDs to delete")


class BulkTagAssignRequest(BaseModel):
    """Request to bulk assign tags"""

    content_ids: list[int] = Field(..., min_length=1, description="List of content IDs")
    tag_ids: list[int] = Field(..., min_length=1, description="List of tag IDs to assign")


class BulkCategoryUpdateRequest(BaseModel):
    """Request to bulk update category"""

    content_ids: list[int] = Field(..., min_length=1, description="List of content IDs")
    category_id: int = Field(..., description="New category ID")


class BulkUserRoleUpdateRequest(BaseModel):
    """Request to bulk update user roles"""

    user_ids: list[int] = Field(..., min_length=1, description="List of user IDs")
    role_id: int = Field(..., description="New role ID")


class BulkOperationResponse(BaseModel):
    """Generic bulk operation response"""

    model_config = ConfigDict(from_attributes=True)

    success_count: int = Field(..., description="Number of successful operations")
    failed_count: int | None = Field(0, description="Number of failed operations")
    success_ids: list[int] | None = Field(None, description="List of successful IDs")
    failed_items: list[dict[str, Any]] | None = Field(None, description="List of failed items with reasons")
    message: str | None = Field(None, description="Additional message")
