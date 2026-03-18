"""Schemas for export functionality."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ExportFormat(StrEnum):
    """Supported export formats."""

    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"
    BIBTEX = "bibtex"
    ANNOTATED_BIBLIOGRAPHY = "annotated_bibliography"


class ExportOptions(BaseModel):
    """Options for export customization."""

    include_abstracts: bool = True
    include_summaries: bool = True
    include_key_findings: bool = True
    include_evidence: bool = False
    include_full_text: bool = False
    include_metadata: bool = True
    custom_fields: list[str] = Field(default_factory=list)


class ExportRequest(BaseModel):
    """Request to export documents."""

    project_id: int
    document_ids: list[int] | None = None  # None = all documents in project
    format: ExportFormat
    options: ExportOptions = Field(default_factory=ExportOptions)
    filename: str | None = None  # Auto-generated if not provided


class ExportResponse(BaseModel):
    """Response containing exported content."""

    content: str
    filename: str
    content_type: str
    document_count: int
    exported_at: datetime = Field(default_factory=datetime.utcnow)


class ExportPreviewRequest(BaseModel):
    """Request to preview export."""

    project_id: int
    format: ExportFormat
    limit: int = Field(default=5, ge=1, le=20)
    options: ExportOptions = Field(default_factory=ExportOptions)


class ExportPreviewResponse(BaseModel):
    """Preview of export content."""

    preview: str
    total_documents: int
    preview_count: int
    format: ExportFormat


# Content type mapping
EXPORT_CONTENT_TYPES = {
    ExportFormat.CSV: "text/csv",
    ExportFormat.JSON: "application/json",
    ExportFormat.MARKDOWN: "text/markdown",
    ExportFormat.BIBTEX: "application/x-bibtex",
    ExportFormat.ANNOTATED_BIBLIOGRAPHY: "text/markdown",
}

# File extension mapping
EXPORT_EXTENSIONS = {
    ExportFormat.CSV: ".csv",
    ExportFormat.JSON: ".json",
    ExportFormat.MARKDOWN: ".md",
    ExportFormat.BIBTEX: ".bib",
    ExportFormat.ANNOTATED_BIBLIOGRAPHY: ".md",
}
