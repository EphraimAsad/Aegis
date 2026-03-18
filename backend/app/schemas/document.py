"""Document schemas for API requests/responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.paper import Author, DocumentType, Identifier, Journal


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class DocumentChunkResponse(BaseModel):
    """Response schema for a document chunk."""

    id: int
    document_id: int
    content: str
    chunk_index: int
    start_char: int | None = None
    end_char: int | None = None
    section_type: str | None = None
    section_title: str | None = None
    token_count: int | None = None
    char_count: int | None = None
    has_embedding: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentBase(BaseModel):
    """Base schema for document data."""

    title: str = Field(..., min_length=1)
    abstract: str | None = None
    authors: list[Author] = Field(default_factory=list)
    document_type: DocumentType = DocumentType.JOURNAL_ARTICLE
    publication_date: str | None = None
    year: int | None = Field(None, ge=1900, le=2100)
    journal: Journal | None = None
    language: str | None = None
    doi: str | None = None
    identifiers: list[Identifier] = Field(default_factory=list)
    url: str | None = None
    pdf_url: str | None = None
    open_access_url: str | None = None
    citation_count: int | None = Field(None, ge=0)
    reference_count: int | None = Field(None, ge=0)
    keywords: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    mesh_terms: list[str] = Field(default_factory=list)
    is_open_access: bool = False
    is_preprint: bool = False
    is_retracted: bool = False
    source_name: str | None = None
    source_id: str | None = None
    source_url: str | None = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""

    project_id: int
    tags: list[str] = Field(default_factory=list)


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    title: str | None = None
    abstract: str | None = None
    tags: list[str] | None = None
    relevance_score: float | None = Field(None, ge=0.0, le=1.0)


class DocumentResponse(DocumentBase):
    """Response schema for a document."""

    id: int
    project_id: int
    status: DocumentStatus
    error_message: str | None = None
    tags: list[str] = Field(default_factory=list)
    full_text: str | None = None
    full_text_source: str | None = None
    summary: str | None = None
    key_findings: list[dict] | None = None
    evidence_claims: list[dict] | None = None
    chunk_count: int = 0
    embedding_model: str | None = None
    relevance_score: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentSummary(BaseModel):
    """Lightweight document summary for lists."""

    id: int
    project_id: int
    title: str
    authors: list[Author] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    status: DocumentStatus
    is_open_access: bool = False
    citation_count: int | None = None
    has_summary: bool = False
    has_full_text: bool = False
    chunk_count: int = 0
    tags: list[str] = Field(default_factory=list)
    relevance_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[DocumentSummary]
    total: int
    page: int
    page_size: int
    has_more: bool


class AddPaperRequest(BaseModel):
    """Request to add a paper from search results to the library."""

    doi: str | None = Field(None, description="DOI of the paper")
    source_name: str | None = Field(None, description="Source to fetch from")
    source_id: str | None = Field(None, description="ID in source system")
    tags: list[str] = Field(default_factory=list, description="Initial tags")


class BulkAddPapersRequest(BaseModel):
    """Request to add multiple papers."""

    papers: list[AddPaperRequest]


class BulkAddPapersResponse(BaseModel):
    """Response from bulk add operation."""

    added: int
    skipped: int
    errors: list[dict]


class ProcessingRequest(BaseModel):
    """Request to trigger document processing."""

    generate_summary: bool = True
    extract_evidence: bool = True
    auto_tag: bool = True


class ProcessingStatus(BaseModel):
    """Status of document processing."""

    document_id: int
    status: DocumentStatus
    chunk_count: int
    has_summary: bool
    has_evidence: bool
    has_tags: bool
    error_message: str | None = None


class SimilarChunkResult(BaseModel):
    """Result from similarity search."""

    chunk_id: int
    document_id: int
    document_title: str
    content: str
    section_type: str | None = None
    similarity_score: float


class SemanticSearchRequest(BaseModel):
    """Request for semantic search."""

    query: str = Field(..., min_length=2)
    top_k: int = Field(10, ge=1, le=100)
    min_similarity: float = Field(0.5, ge=0.0, le=1.0)
    document_ids: list[int] | None = None
    section_types: list[str] | None = None


class SemanticSearchResponse(BaseModel):
    """Response from semantic search."""

    query: str
    results: list[SimilarChunkResult]
    total_results: int
