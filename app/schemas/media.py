"""
Media Schemas

Pydantic models for media upload, search, folders, and responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MediaResponse(BaseModel):
    """Media response schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    mime_type: str
    file_type: str
    width: int | None = None
    height: int | None = None
    thumbnail_path: str | None = None
    alt_text: str | None = None
    title: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    folder_id: int | None = None
    sizes: dict[str, str] = Field(default_factory=dict)
    uploaded_by: int
    uploaded_at: datetime
    updated_at: datetime | None = None


class MediaUploadResponse(BaseModel):
    """Response after successful upload"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    mime_type: str
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    sizes: dict[str, str] = Field(default_factory=dict)
    uploaded_at: datetime


class MediaListResponse(BaseModel):
    """Response for listing media"""

    model_config = ConfigDict(from_attributes=True)

    media: list[MediaResponse]
    total: int
    limit: int
    offset: int


class MediaUpdateRequest(BaseModel):
    """Request to update media metadata"""

    alt_text: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    tags: list[str] | None = Field(None)
    folder_id: int | None = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            v = [tag.strip().lower() for tag in v if tag.strip()]
            if len(v) > 20:
                msg = "Maximum 20 tags allowed"
                raise ValueError(msg)
        return v


class MediaSearchParams(BaseModel):
    """Query parameters for media search"""

    query: str | None = Field(None, description="Search in filename, alt_text, title")
    file_type: str | None = Field(None, description="Filter by file_type (image, document)")
    folder_id: int | None = Field(None, description="Filter by folder")
    tags: str | None = Field(None, description="Comma-separated tags to filter by")
    min_size: int | None = Field(None, description="Minimum file size in bytes")
    max_size: int | None = Field(None, description="Maximum file size in bytes")
    uploaded_after: datetime | None = None
    uploaded_before: datetime | None = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class BulkMediaDeleteRequest(BaseModel):
    """Request to delete multiple media items"""

    media_ids: list[int] = Field(..., min_length=1, max_length=100)


class BulkMediaMoveRequest(BaseModel):
    """Request to move multiple media items to a folder"""

    media_ids: list[int] = Field(..., min_length=1, max_length=100)
    folder_id: int | None = None  # None = move to root


class BulkOperationResponse(BaseModel):
    """Response for bulk operations"""

    success_count: int
    failed_count: int
    failed_items: list[dict[str, Any]] = Field(default_factory=list)


class MediaFolderCreate(BaseModel):
    """Request to create a media folder"""

    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int | None = None


class MediaFolderUpdate(BaseModel):
    """Request to update a media folder"""

    name: str = Field(..., min_length=1, max_length=100)


class MediaFolderResponse(BaseModel):
    """Media folder response schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    parent_id: int | None
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None


class MediaFolderListResponse(BaseModel):
    """Response for listing folders"""

    folders: list[MediaFolderResponse]
