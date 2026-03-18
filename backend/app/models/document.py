"""Document model for storing processed papers."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class DocumentStatus(StrEnum):
    """Document processing status."""

    PENDING = "pending"  # Just added, not processed
    DOWNLOADING = "downloading"  # Downloading full text
    PROCESSING = "processing"  # Being chunked/embedded
    READY = "ready"  # Fully processed
    ERROR = "error"  # Processing failed


class Document(Base):
    """
    Stored academic document.

    Represents a paper that has been added to a project's library,
    including metadata, full text (if available), and processing status.
    """

    __tablename__ = "documents"

    # Project relationship
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Processing status
    status: Mapped[DocumentStatus] = mapped_column(
        String(50),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Core metadata (from Paper schema)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Authors stored as JSON array
    authors: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
    )
    # Format: [{"name": "...", "orcid": "...", "affiliations": [...]}]

    # Publication info
    document_type: Mapped[str] = mapped_column(String(50), default="journal-article")
    publication_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Journal info as JSON
    journal: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Format: {"name": "...", "issn": "...", "volume": "...", "issue": "...", "pages": "..."}

    language: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Identifiers
    doi: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )
    identifiers: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    # Format: [{"type": "pmid", "value": "12345678"}]

    # URLs
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    open_access_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Classification
    keywords: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    subjects: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)
    mesh_terms: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)

    # Tags (user-defined and auto-generated)
    tags: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True)

    # Flags
    is_open_access: Mapped[bool] = mapped_column(Boolean, default=False)
    is_preprint: Mapped[bool] = mapped_column(Boolean, default=False)
    is_retracted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source tracking
    source_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Full text content (if available)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Generated content
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_findings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    evidence_claims: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Format: [{"claim": "...", "evidence": "...", "confidence": 0.9, "location": "..."}]

    # Processing metadata
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relevance to project (computed)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title[:50]}...', status='{self.status}')>"


class DocumentChunk(Base):
    """
    Text chunk from a document with embedding.

    Documents are split into smaller chunks for embedding and retrieval.
    Each chunk maintains its position and relationship to the source.
    """

    __tablename__ = "document_chunks"

    # Document relationship
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Position in source
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Section info (if available)
    section_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # e.g., "abstract", "introduction", "methods", "results", "discussion", "conclusion"

    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Chunk metadata
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Embedding stored as JSON array (for compatibility)
    # Will be migrated to pgvector when fully set up
    embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        preview = self.content[:50] if self.content else ""
        return f"<DocumentChunk(id={self.id}, doc={self.document_id}, index={self.chunk_index}, preview='{preview}...')>"
