"""
Search Schemas

Pydantic models for search requests and responses.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content import ContentResponse

# ============================================================================
# Legacy schemas (backward compatibility with /api/v1/content/search/ endpoints)
# ============================================================================


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


# ============================================================================
# Full-Text Search schemas (for /api/v1/search/ endpoints)
# ============================================================================


class SearchResultItem(BaseModel):
    """Single search result with relevance score and highlights"""

    model_config = ConfigDict(from_attributes=True)

    content: ContentResponse
    relevance_score: float = Field(..., description="Relevance ranking score")
    highlights: dict[str, str] | None = Field(
        None, description="Highlighted snippets by field (title, body, description)"
    )


class FacetBucket(BaseModel):
    """Single facet value with count"""

    value: str
    label: str
    count: int


class SearchFacets(BaseModel):
    """Faceted search results"""

    categories: list[FacetBucket] = []
    tags: list[FacetBucket] = []
    statuses: list[FacetBucket] = []
    authors: list[FacetBucket] = []


class FullTextSearchResponse(BaseModel):
    """Enhanced search response with relevance scoring, highlights, and facets"""

    model_config = ConfigDict(from_attributes=True)

    results: list[SearchResultItem]
    total: int = Field(..., description="Total number of matching results")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether there are more results")
    query: str = Field(..., description="The search query")
    facets: SearchFacets | None = Field(None, description="Faceted search counts")
    execution_time_ms: float | None = Field(None, description="Search execution time in milliseconds")


class SearchSuggestion(BaseModel):
    """Autocomplete suggestion"""

    id: int
    title: str
    slug: str


class SearchSuggestionsResponse(BaseModel):
    """Suggestions/autocomplete response"""

    suggestions: list[SearchSuggestion]
    query: str


class SearchAnalyticsResponse(BaseModel):
    """Search analytics data"""

    total_searches: int
    unique_queries: int
    avg_results_count: float
    avg_execution_time_ms: float
    top_queries: list[dict]
    zero_result_queries: list[dict]
    searches_over_time: list[dict]
