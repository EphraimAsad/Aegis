"""Schemas for analytics and insights."""

from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    """Overview statistics for a project."""

    project_id: int
    total_documents: int = 0
    documents_by_status: dict[str, int] = Field(default_factory=dict)
    documents_by_year: dict[int, int] = Field(default_factory=dict)
    total_citations: int = 0
    avg_citations: float = 0.0
    unique_authors: int = 0
    unique_journals: int = 0
    open_access_count: int = 0
    preprint_count: int = 0
    documents_with_full_text: int = 0
    documents_with_summary: int = 0
    embedding_coverage: float = 0.0  # Percentage of documents with embeddings


class PublicationTrend(BaseModel):
    """Publication trend data point."""

    year: int
    count: int
    citation_total: int = 0
    citation_avg: float = 0.0
    open_access_count: int = 0


class AuthorStats(BaseModel):
    """Statistics for an author."""

    name: str
    document_count: int
    total_citations: int = 0
    first_year: int | None = None
    last_year: int | None = None
    affiliations: list[str] = Field(default_factory=list)


class KeywordStats(BaseModel):
    """Statistics for a keyword/tag."""

    keyword: str
    count: int
    related_keywords: list[str] = Field(default_factory=list)


class SourceStats(BaseModel):
    """Statistics for a source."""

    source_name: str
    document_count: int
    avg_citations: float = 0.0


class DocumentTypeStats(BaseModel):
    """Statistics for a document type."""

    document_type: str
    count: int
    percentage: float = 0.0


class AnalyticsTrends(BaseModel):
    """Publication trends response."""

    project_id: int
    trends: list[PublicationTrend]
    from_year: int | None = None
    to_year: int | None = None


class AnalyticsAuthors(BaseModel):
    """Top authors response."""

    project_id: int
    authors: list[AuthorStats]
    total_unique_authors: int


class AnalyticsKeywords(BaseModel):
    """Keywords/tags response."""

    project_id: int
    keywords: list[KeywordStats]
    tags: list[KeywordStats]


class AnalyticsDashboard(BaseModel):
    """Complete analytics dashboard data."""

    overview: AnalyticsOverview
    publication_trends: list[PublicationTrend] = Field(default_factory=list)
    top_authors: list[AuthorStats] = Field(default_factory=list)
    top_keywords: list[KeywordStats] = Field(default_factory=list)
    top_tags: list[KeywordStats] = Field(default_factory=list)
    source_distribution: list[SourceStats] = Field(default_factory=list)
    document_type_distribution: list[DocumentTypeStats] = Field(default_factory=list)
