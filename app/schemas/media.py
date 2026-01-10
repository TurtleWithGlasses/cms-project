"""
Media Schemas

Pydantic models for media upload and responses.
"""

from datetime import datetime

from pydantic import BaseModel


class MediaResponse(BaseModel):
    """Media response schema"""

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

    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    """Response after successful upload"""

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

    class Config:
        from_attributes = True


class MediaListResponse(BaseModel):
    """Response for listing media"""

    media: list[MediaResponse]
    total: int
    limit: int
    offset: int

    class Config:
        from_attributes = True
