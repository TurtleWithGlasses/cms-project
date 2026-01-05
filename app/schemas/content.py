from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum
from app.utils.sanitize import (
    sanitize_content_title,
    sanitize_content_body,
    sanitize_meta_description,
    sanitize_plain_text
)

class ContentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

status: ContentStatus = Field(ContentStatus.DRAFT, title="Content Status", description="The status of the content.")


class ContentCreate(BaseModel):
    title: str = Field(..., title="Content Title", description="The title of the content.")
    body: str = Field(..., title="Content Body", description="The main body of the content.")
    description: str = Field(..., title="Description", description="A short description of the content.")
    status: str = Field(ContentStatus.DRAFT, title="Content Status")
    slug: Optional[str] = Field(None, title="Slug", description="Slug for the content.")
    meta_title: Optional[str] = Field(None, title="Meta Title", description="SEO title for the content.")
    meta_description: Optional[str] = Field(None, title="Meta Description", description="SEO description for the content.")
    meta_keywords: Optional[str] = Field(None, title="Meta Keywords", description="SEO keywords for the content.")
    publish_at: Optional[datetime] = Field(None, description="When the content should be published")

    @field_validator('title', 'meta_title')
    @classmethod
    def sanitize_title_fields(cls, v):
        """Sanitize title fields - strip HTML"""
        return sanitize_content_title(v) if v else v

    @field_validator('body')
    @classmethod
    def sanitize_body_field(cls, v):
        """Sanitize body - allow safe HTML"""
        return sanitize_content_body(v) if v else v

    @field_validator('description', 'meta_description', 'meta_keywords')
    @classmethod
    def sanitize_meta_fields(cls, v):
        """Sanitize meta fields - strip HTML"""
        return sanitize_meta_description(v) if v else v

    @field_validator('slug')
    @classmethod
    def sanitize_slug_field(cls, v):
        """Sanitize slug - strip HTML and special chars"""
        return sanitize_plain_text(v) if v else v

class ContentUpdate(BaseModel):
    title: Optional[str] = Field(None, title="Updated Title", description="The updated title of the content.")
    body: Optional[str] = Field(None, title="Updated Body", description="The updated body of the content.")
    slug: Optional[str] = Field(None, title="Slug", description="The slugified version of the content title for URL purposes.")
    meta_title: Optional[str] = Field(None, title="Meta Title", description="SEO title for the content.")
    meta_description: Optional[str] = Field(None, title="Meta Description", description="SEO description for the content.")
    meta_keywords: Optional[str] = Field(None, title="Meta Keywords", description="SEO keywords for the content.")
    status: Optional[ContentStatus] = Field(None, title="Content Status", description="The updated status of the content.")
    publish_at: Optional[datetime] = Field(None, description="When the content should be published")

    @field_validator('title', 'meta_title')
    @classmethod
    def sanitize_title_fields(cls, v):
        """Sanitize title fields - strip HTML"""
        return sanitize_content_title(v) if v else v

    @field_validator('body')
    @classmethod
    def sanitize_body_field(cls, v):
        """Sanitize body - allow safe HTML"""
        return sanitize_content_body(v) if v else v

    @field_validator('meta_description', 'meta_keywords')
    @classmethod
    def sanitize_meta_fields(cls, v):
        """Sanitize meta fields - strip HTML"""
        return sanitize_meta_description(v) if v else v

    @field_validator('slug')
    @classmethod
    def sanitize_slug_field(cls, v):
        """Sanitize slug - strip HTML and special chars"""
        return sanitize_plain_text(v) if v else v

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Updated Content Title",
            "body": "Updated content body text.",
            "slug": "updated-content-title",
            "meta_title": "Updated Meta Title",
            "meta_description": "Updated meta description for the content.",
            "meta_keywords": "updated, content, keywords",
            "status": "published",
        }
    })

class ContentResponse(BaseModel):
    id: int = Field(..., title="Content ID", description="The unique identifier for the content.")
    title: str = Field(..., title="Content Title", description="The title of the content.")
    body: str = Field(..., title="Content Body", description="The body of the content.")
    status: ContentStatus = Field(..., title="Content Status", description="The status of the content (e.g., draft, published).")
    created_at: datetime = Field(..., title="Created At", description="The timestamp when the content was created.")
    updated_at: datetime = Field(..., title="Updated At", description="The timestamp when the content was last updated.")
    author_id: int = Field(..., title="Author ID", description="The ID of the user who authored the content.")

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Example Content Title",
                "body": "This is the body of the example content.",
                "status": "draft",
                "created_at": "2024-11-22T12:00:00.000Z",
                "updated_at": "2024-11-22T12:30:00.000Z",
                "author_id": 42,
            }
        }
    )
