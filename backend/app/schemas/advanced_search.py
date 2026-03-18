"""Schemas for advanced search functionality."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.document import DocumentSummary


class DateFilter(BaseModel):
    """Filter by date range."""

    from_year: int | None = None
    to_year: int | None = None


class MetricsFilter(BaseModel):
    """Filter by citation metrics."""

    min_citations: int | None = None
    max_citations: int | None = None


class AdvancedSearchFilters(BaseModel):
    """Filters for advanced document search."""

    # Text search
    query: str | None = None  # Keyword search in title/abstract
    semantic_query: str | None = None  # Semantic search query

    # Tags and keywords
    tags: list[str] = Field(default_factory=list)
    exclude_tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)

    # Date range
    date_filter: DateFilter | None = None

    # Authors
    authors: list[str] = Field(default_factory=list)

    # Journals
    journals: list[str] = Field(default_factory=list)

    # Document types
    document_types: list[str] = Field(default_factory=list)

    # Status
    statuses: list[str] = Field(default_factory=list)

    # Metrics
    metrics_filter: MetricsFilter | None = None

    # Flags
    open_access_only: bool = False
    has_full_text: bool | None = None
    has_summary: bool | None = None
    exclude_preprints: bool = False
    exclude_retracted: bool = True

    # Source
    sources: list[str] = Field(default_factory=list)


class SearchFacets(BaseModel):
    """Aggregated facet counts for search results."""

    years: dict[int, int] = Field(default_factory=dict)
    authors: dict[str, int] = Field(default_factory=dict)
    journals: dict[str, int] = Field(default_factory=dict)
    tags: dict[str, int] = Field(default_factory=dict)
    document_types: dict[str, int] = Field(default_factory=dict)
    sources: dict[str, int] = Field(default_factory=dict)


class AdvancedSearchRequest(BaseModel):
    """Request for advanced search."""

    project_id: int
    filters: AdvancedSearchFilters = Field(default_factory=AdvancedSearchFilters)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    include_facets: bool = True
    sort_by: str = "relevance"  # relevance, year, citations, title
    sort_order: str = "desc"  # asc, desc


class AdvancedSearchResponse(BaseModel):
    """Response for advanced search."""

    documents: list[DocumentSummary]
    total: int
    page: int
    page_size: int
    has_more: bool
    facets: SearchFacets | None = None
    query_used: str | None = None


class SearchSuggestion(BaseModel):
    """Search suggestion/autocomplete item."""

    text: str
    type: str  # author, keyword, tag, journal
    count: int


class SearchSuggestionsResponse(BaseModel):
    """Response for search suggestions."""

    suggestions: list[SearchSuggestion]
    query: str
