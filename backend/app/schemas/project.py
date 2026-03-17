"""Project-related schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Project lifecycle status."""

    DRAFT = "draft"
    CLARIFYING = "clarifying"
    READY = "ready"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ProjectScope(BaseModel):
    """Project scope definition."""

    disciplines: list[str] = Field(default_factory=list, description="Academic disciplines")
    keywords: list[str] = Field(default_factory=list, description="Search keywords")
    excluded_keywords: list[str] = Field(default_factory=list, description="Keywords to exclude")
    date_range_start: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    date_range_end: str | None = Field(None, description="End date (YYYY-MM-DD)")
    languages: list[str] = Field(default_factory=lambda: ["en"], description="Languages")
    document_types: list[str] = Field(
        default_factory=lambda: ["journal-article", "conference-paper"],
        description="Document types",
    )
    min_citations: int = Field(0, ge=0, description="Minimum citation count")
    include_preprints: bool = Field(True, description="Include preprints")
    geographic_focus: list[str] = Field(default_factory=list, description="Geographic regions")
    specific_journals: list[str] = Field(default_factory=list, description="Specific journals")
    specific_authors: list[str] = Field(default_factory=list, description="Specific authors")
    custom_filters: dict = Field(default_factory=dict, description="Custom filters")


# Request schemas


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Project description")
    research_objective: str = Field(..., min_length=10, description="Research objective/question")
    provider: str | None = Field(None, description="AI provider override")
    model: str | None = Field(None, description="Model override")


class ProjectUpdateRequest(BaseModel):
    """Request to update a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    research_objective: str | None = Field(None, min_length=10)
    provider: str | None = None
    model: str | None = None
    max_results_per_source: int | None = Field(None, ge=1, le=1000)
    sources_enabled: list[str] | None = None


class ProjectScopeUpdateRequest(BaseModel):
    """Request to update project scope."""

    scope: ProjectScope


class ProjectStatusUpdateRequest(BaseModel):
    """Request to update project status."""

    status: ProjectStatus


# Response schemas


class ProjectSummary(BaseModel):
    """Summary view of a project."""

    id: int
    name: str
    status: ProjectStatus
    research_objective: str
    created_at: datetime
    updated_at: datetime
    unanswered_questions: int = 0

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    """Detailed view of a project."""

    id: int
    name: str
    description: str | None
    research_objective: str
    status: ProjectStatus
    scope: ProjectScope | None
    provider: str | None
    model: str | None
    max_results_per_source: int
    sources_enabled: list[str]
    created_at: datetime
    updated_at: datetime
    is_scope_complete: bool
    unanswered_questions: int = 0
    is_ready_for_research: bool

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Response for listing projects."""

    projects: list[ProjectSummary]
    total: int
    page: int
    page_size: int
