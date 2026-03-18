"""Job progress log model for agent memory and checkpointing."""

from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.job import Job


class LogEntryType(StrEnum):
    """Types of progress log entries."""

    # Workflow phases
    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"

    # Discoveries/findings
    PAPER_FOUND = "paper_found"
    PAPER_COLLECTED = "paper_collected"
    PAPER_PROCESSED = "paper_processed"
    INSIGHT = "insight"
    THEME = "theme"

    # Checkpoints
    CHECKPOINT = "checkpoint"

    # Errors and recovery
    ERROR = "error"
    RECOVERY = "recovery"

    # Resource tracking
    API_CALL = "api_call"

    # General
    INFO = "info"
    DEBUG = "debug"


class JobProgressLog(Base):
    """
    Progress log entry for job memory and checkpointing.

    Stores structured entries for:
    - Agent findings (papers, insights, themes)
    - Workflow checkpoints for resumption
    - Error tracking and recovery
    - Resource usage logging

    This enables long-running research jobs to:
    - Persist findings incrementally
    - Resume from checkpoints after worker restarts
    - Track detailed progress for visibility
    """

    __tablename__ = "job_progress_logs"

    # Link to job
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Entry type and phase
    entry_type: Mapped[LogEntryType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    phase: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )  # e.g., "search", "collect", "process", "synthesize"

    # Human-readable message
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured data (entry-type specific)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Data structures by entry_type:
    # - PAPER_FOUND: {"doi": "...", "title": "...", "source": "...", "relevance_score": 0.9}
    # - PAPER_COLLECTED: {"document_id": 123, "doi": "...", "title": "..."}
    # - INSIGHT: {"claim": "...", "evidence": "...", "documents": [1, 2, 3]}
    # - THEME: {"name": "...", "description": "...", "document_count": 5}
    # - CHECKPOINT: {"step": 3, "step_name": "..."}
    # - API_CALL: {"provider": "openai", "model": "gpt-4", "tokens": 300}
    # - ERROR: {"error_type": "...", "error_message": "...", "recoverable": true}

    # Checkpoint-specific fields
    is_checkpoint: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )
    checkpoint_state: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    # Checkpoint state structure:
    # {
    #     "current_step": 3,
    #     "step_name": "process_documents",
    #     "items_processed": [1, 2, 3, 4],  # Document IDs already processed
    #     "items_remaining": [5, 6, 7],      # Document IDs still to process
    #     "search_cursors": {"openalex": "...", "crossref": "..."},
    #     "accumulated_results": {...},      # Partial results to preserve
    #     "context_summary": "..."           # Summary of work done
    # }

    # Ordering (auto-incrementing per job for deterministic ordering)
    sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="progress_logs")

    def __repr__(self) -> str:
        return f"<JobProgressLog(id={self.id}, job_id={self.job_id}, type='{self.entry_type}')>"
