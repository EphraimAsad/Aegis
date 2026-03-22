"""Project model for research projects."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.clarification import ClarificationQuestion
    from app.models.document import Document
    from app.models.job import Job


class ProjectStatus(StrEnum):
    """Project lifecycle status."""

    DRAFT = "draft"  # Initial creation, objective entered
    CLARIFYING = "clarifying"  # Clarification questions being asked
    READY = "ready"  # Scope defined, ready to start research
    ACTIVE = "active"  # Research in progress
    COMPLETED = "completed"  # Research finished
    ARCHIVED = "archived"  # Project archived


class Project(Base):
    """
    Research project model.

    Represents a research project with its objective, scope,
    and configuration for AI-assisted literature review.
    """

    __tablename__ = "projects"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Research objective - the main research question/goal
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)

    # Project status
    status: Mapped[ProjectStatus] = mapped_column(
        String(50),
        default=ProjectStatus.DRAFT,
        nullable=False,
    )

    # Scope definition (structured fields)
    scope: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    # Scope structure:
    # {
    #     "disciplines": ["computer science", "biology"],
    #     "keywords": ["machine learning", "protein folding"],
    #     "excluded_keywords": ["unrelated term"],
    #     "date_range_start": "2020-01-01",
    #     "date_range_end": "2024-12-31",
    #     "languages": ["en"],
    #     "document_types": ["journal-article", "conference-paper"],
    #     "min_citations": 0,
    #     "include_preprints": true,
    #     "geographic_focus": [],
    #     "specific_journals": [],
    #     "specific_authors": [],
    #     "custom_filters": {}
    # }

    # Provider/model configuration for this project
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Search configuration
    max_results_per_source: Mapped[int] = mapped_column(Integer, default=100)
    sources_enabled: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: ["openalex", "crossref", "semantic_scholar", "arxiv", "pubmed"],
    )

    # Relationships
    clarification_questions: Mapped[list["ClarificationQuestion"]] = relationship(
        "ClarificationQuestion",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ClarificationQuestion.order",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>"

    @property
    def is_scope_complete(self) -> bool:
        """Check if the project scope is sufficiently defined."""
        if not self.scope:
            return False

        # Minimum requirements for a complete scope
        required_fields = ["keywords"]
        for field in required_fields:
            if not self.scope.get(field):
                return False

        return True

    @property
    def unanswered_questions_count(self) -> int:
        """Count unanswered clarification questions."""
        return sum(1 for q in self.clarification_questions if not q.is_answered)

    @property
    def is_ready_for_research(self) -> bool:
        """Check if the project is ready to begin research."""
        # Archived projects cannot start research
        if self.status == ProjectStatus.ARCHIVED:
            return False
        # Projects with unanswered questions are not ready
        if self.unanswered_questions_count > 0:
            return False
        # Ready if draft, clarifying (all questions answered), or ready
        return self.status in (
            ProjectStatus.READY,
            ProjectStatus.DRAFT,
            ProjectStatus.CLARIFYING,
        )
