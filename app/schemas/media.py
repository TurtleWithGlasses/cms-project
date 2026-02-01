"""
Media Schemas

Pydantic models for media upload and responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
    uploaded_by: int
    uploaded_at: datetime


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
    uploaded_at: datetime


class MediaListResponse(BaseModel):
    """Response for listing media"""

    model_config = ConfigDict(from_attributes=True)

    media: list[MediaResponse]
    total: int
    limit: int
    offset: int
