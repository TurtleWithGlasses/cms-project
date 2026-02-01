"""
Search Schemas

Pydantic models for search requests and responses.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import ContentResponse


class SearchRequest(BaseModel):
    """Search request parameters"""

    query: str | None = Field(None, description="Search query string")
    category_id: int | None = Field(None, description="Filter by category ID")
    tag_ids: list[int] | None = Field(None, description="Filter by tag IDs")
    status: str | None = Field(None, description="Filter by content status")
    author_id: int | None = Field(None, description="Filter by author ID")
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")
    limit: int = Field(20, ge=1, le=100, description="Maximum results per page")
    offset: int = Field(0, ge=0, description="Pagination offset")


class SearchResponse(BaseModel):
    """Search response with results and pagination"""

    model_config = ConfigDict(from_attributes=True)

    results: list[ContentResponse]
    total: int = Field(..., description="Total number of matching results")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether there are more results")


class PopularTagResponse(BaseModel):
    """Popular tag with usage count"""

    model_config = ConfigDict(from_attributes=True)

    name: str
    count: int
