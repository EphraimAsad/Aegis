"""Job model for tracking background tasks."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class JobType(str, Enum):
    """Types of background jobs."""

    # Document processing
    PROCESS_DOCUMENT = "process_document"
    EMBED_DOCUMENT = "embed_document"
    SUMMARIZE_DOCUMENT = "summarize_document"
    BATCH_PROCESS = "batch_process"

    # Research jobs
    RESEARCH_FULL = "research_full"
    SEARCH_COLLECT = "search_collect"
    ANALYZE_COLLECTION = "analyze_collection"

    # Maintenance
    CLEANUP = "cleanup"
    REINDEX = "reindex"


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"  # Queued, not started
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Error occurred
    CANCELLED = "cancelled"  # User cancelled
    PAUSED = "paused"  # Temporarily paused


class JobPriority(str, Enum):
    """Job priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Job(Base):
    """
    Background job tracking model.

    Tracks the status and progress of long-running tasks
    like document processing and research workflows.
    """

    __tablename__ = "jobs"

    # Job identification
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )
    job_type: Mapped[JobType] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[JobStatus] = mapped_column(
        String(50),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[JobPriority] = mapped_column(
        String(20),
        default=JobPriority.NORMAL,
        nullable=False,
    )

    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    progress_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=1)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    estimated_completion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Input/Output
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Statistics
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_total: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Resource tracking
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    api_calls_made: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project: Mapped["Project | None"] = relationship("Project", back_populates="jobs")

    # Parent job (for sub-tasks)
    parent_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parent_job: Mapped["Job | None"] = relationship(
        "Job",
        remote_side="Job.id",
        back_populates="child_jobs",
    )
    child_jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="parent_job",
        cascade="all, delete-orphan",
    )

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, type='{self.job_type}', status='{self.status}')>"

    @property
    def is_active(self) -> bool:
        """Check if job is currently active."""
        return self.status in [JobStatus.PENDING, JobStatus.RUNNING, JobStatus.PAUSED]

    @property
    def is_finished(self) -> bool:
        """Check if job has finished (success or failure)."""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]

    @property
    def duration_seconds(self) -> float | None:
        """Calculate job duration in seconds."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()

    @property
    def progress_percent(self) -> int:
        """Get progress as percentage."""
        return int(self.progress * 100)

    def update_progress(
        self,
        progress: float | None = None,
        message: str | None = None,
        current_step: int | None = None,
        items_processed: int | None = None,
    ) -> None:
        """Update job progress."""
        if progress is not None:
            self.progress = min(max(progress, 0.0), 1.0)
        if message is not None:
            self.progress_message = message
        if current_step is not None:
            self.current_step = current_step
            if self.total_steps > 0:
                self.progress = current_step / self.total_steps
        if items_processed is not None:
            self.items_processed = items_processed
            if self.items_total > 0:
                self.progress = items_processed / self.items_total

    def mark_started(self) -> None:
        """Mark job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result: dict | None = None) -> None:
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 1.0
        if result:
            self.result_data = result

    def mark_failed(self, error: str, traceback: str | None = None) -> None:
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error
        self.error_traceback = traceback

    def mark_cancelled(self) -> None:
        """Mark job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
