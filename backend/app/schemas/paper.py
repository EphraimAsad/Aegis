"""Normalized paper/document schemas for academic sources."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class DocumentType(str, Enum):
    """Types of academic documents."""

    JOURNAL_ARTICLE = "journal-article"
    CONFERENCE_PAPER = "conference-paper"
    BOOK = "book"
    BOOK_CHAPTER = "book-chapter"
    PREPRINT = "preprint"
    THESIS = "thesis"
    DISSERTATION = "dissertation"
    REPORT = "report"
    DATASET = "dataset"
    REVIEW = "review"
    OTHER = "other"


class Author(BaseModel):
    """Author information."""

    name: str = Field(..., description="Full name")
    given_name: str | None = Field(None, description="First/given name")
    family_name: str | None = Field(None, description="Last/family name")
    orcid: str | None = Field(None, description="ORCID identifier")
    affiliations: list[str] = Field(default_factory=list, description="Institutional affiliations")


class Identifier(BaseModel):
    """External identifier for a paper."""

    type: str = Field(..., description="Identifier type (doi, pmid, arxiv, etc.)")
    value: str = Field(..., description="Identifier value")


class SourceInfo(BaseModel):
    """Information about the source that provided this paper."""

    name: str = Field(..., description="Source name (openalex, crossref, etc.)")
    id: str = Field(..., description="ID in the source system")
    url: HttpUrl | None = Field(None, description="URL in the source system")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)


class Journal(BaseModel):
    """Journal/venue information."""

    name: str | None = Field(None, description="Journal or venue name")
    issn: str | None = Field(None, description="ISSN")
    volume: str | None = Field(None, description="Volume number")
    issue: str | None = Field(None, description="Issue number")
    pages: str | None = Field(None, description="Page range")
    publisher: str | None = Field(None, description="Publisher name")


class Paper(BaseModel):
    """
    Normalized paper/document schema.

    This schema represents academic papers from any source in a unified format.
    All source adapters convert their native format to this schema.
    """

    # Core metadata
    title: str = Field(..., description="Paper title")
    abstract: str | None = Field(None, description="Abstract text")
    authors: list[Author] = Field(default_factory=list, description="List of authors")

    # Publication info
    document_type: DocumentType = Field(DocumentType.JOURNAL_ARTICLE, description="Type of document")
    publication_date: date | None = Field(None, description="Publication date")
    year: int | None = Field(None, description="Publication year")
    journal: Journal | None = Field(None, description="Journal/venue information")
    language: str | None = Field(None, description="Language code (e.g., 'en')")

    # Identifiers
    doi: str | None = Field(None, description="DOI")
    identifiers: list[Identifier] = Field(default_factory=list, description="All identifiers")

    # URLs
    url: HttpUrl | None = Field(None, description="Primary URL")
    pdf_url: HttpUrl | None = Field(None, description="Direct PDF URL if available")
    open_access_url: HttpUrl | None = Field(None, description="Open access URL")

    # Metrics
    citation_count: int | None = Field(None, ge=0, description="Number of citations")
    reference_count: int | None = Field(None, ge=0, description="Number of references")

    # Classification
    keywords: list[str] = Field(default_factory=list, description="Keywords/tags")
    subjects: list[str] = Field(default_factory=list, description="Subject areas/disciplines")
    mesh_terms: list[str] = Field(default_factory=list, description="MeSH terms (for biomedical)")

    # Flags
    is_open_access: bool = Field(False, description="Whether open access")
    is_preprint: bool = Field(False, description="Whether this is a preprint")
    is_retracted: bool = Field(False, description="Whether retracted")

    # Source tracking
    sources: list[SourceInfo] = Field(default_factory=list, description="Sources that provided this paper")
    primary_source: str | None = Field(None, description="Primary source name")

    # Internal
    dedupe_key: str | None = Field(None, description="Key for deduplication")

    def add_source(self, source: SourceInfo) -> None:
        """Add a source to the paper."""
        self.sources.append(source)
        if not self.primary_source:
            self.primary_source = source.name

    def generate_dedupe_key(self) -> str:
        """Generate a deduplication key based on DOI or title+year."""
        if self.doi:
            return f"doi:{self.doi.lower()}"

        # Normalize title for comparison
        title_normalized = "".join(
            c.lower() for c in self.title if c.isalnum()
        )
        year_str = str(self.year) if self.year else "unknown"
        return f"title:{title_normalized[:100]}:{year_str}"


class PaperSearchResult(BaseModel):
    """Result from a paper search."""

    papers: list[Paper] = Field(default_factory=list)
    total_results: int = Field(0, description="Total number of results available")
    query: str = Field(..., description="Search query used")
    source: str = Field(..., description="Source that provided results")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1)
    has_more: bool = Field(False, description="Whether more results are available")


class SearchFilters(BaseModel):
    """Filters for academic paper search."""

    keywords: list[str] = Field(default_factory=list, description="Search keywords")
    title_contains: str | None = Field(None, description="Title must contain")
    author: str | None = Field(None, description="Author name filter")

    year_from: int | None = Field(None, ge=1900, le=2100, description="Start year")
    year_to: int | None = Field(None, ge=1900, le=2100, description="End year")

    document_types: list[DocumentType] = Field(default_factory=list, description="Document type filter")
    languages: list[str] = Field(default_factory=list, description="Language filter")

    open_access_only: bool = Field(False, description="Only open access papers")
    min_citations: int = Field(0, ge=0, description="Minimum citation count")

    journals: list[str] = Field(default_factory=list, description="Specific journals")
    subjects: list[str] = Field(default_factory=list, description="Subject areas")

    exclude_keywords: list[str] = Field(default_factory=list, description="Keywords to exclude")
    exclude_preprints: bool = Field(False, description="Exclude preprints")

    def to_query_string(self) -> str:
        """Convert filters to a basic query string."""
        parts = []

        if self.keywords:
            parts.extend(self.keywords)

        if self.title_contains:
            parts.append(f'title:"{self.title_contains}"')

        if self.author:
            parts.append(f'author:"{self.author}"')

        return " AND ".join(parts) if parts else "*"


class AggregatedSearchResult(BaseModel):
    """Aggregated results from multiple sources."""

    papers: list[Paper] = Field(default_factory=list)
    total_from_sources: dict[str, int] = Field(default_factory=dict)
    deduplicated_count: int = Field(0)
    original_count: int = Field(0)
    query: str = Field(...)
    filters: SearchFilters | None = None
    sources_searched: list[str] = Field(default_factory=list)
    errors: dict[str, str] = Field(default_factory=dict, description="Errors by source")
