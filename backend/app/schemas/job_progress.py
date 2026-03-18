"""Schemas for job progress log API."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LogEntryType(str, Enum):
    """Types of progress log entries."""

    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"
    PAPER_FOUND = "paper_found"
    PAPER_COLLECTED = "paper_collected"
    PAPER_PROCESSED = "paper_processed"
    INSIGHT = "insight"
    THEME = "theme"
    CHECKPOINT = "checkpoint"
    ERROR = "error"
    RECOVERY = "recovery"
    API_CALL = "api_call"
    INFO = "info"
    DEBUG = "debug"


class ProgressLogEntry(BaseModel):
    """A single progress log entry."""

    id: int
    job_id: int
    entry_type: LogEntryType
    phase: str | None = None
    message: str
    data: dict | None = None
    is_checkpoint: bool = False
    sequence: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProgressLogCreate(BaseModel):
    """Schema for creating a progress log entry."""

    entry_type: LogEntryType
    phase: str | None = None
    message: str
    data: dict | None = None
    is_checkpoint: bool = False
    checkpoint_state: dict | None = None


class CheckpointState(BaseModel):
    """Schema for checkpoint state."""

    current_step: int
    step_name: str
    items_processed: list[int] = Field(default_factory=list)
    items_remaining: list[int] = Field(default_factory=list)
    search_cursors: dict[str, str] = Field(default_factory=dict)
    accumulated_results: dict = Field(default_factory=dict)
    context_summary: str | None = None


class ProgressLogList(BaseModel):
    """Response for listing progress logs."""

    entries: list[ProgressLogEntry]
    total: int
    job_id: int


class JobProgressSummary(BaseModel):
    """Summary of job progress."""

    job_id: int
    total_entries: int
    papers_found: int
    papers_collected: int
    papers_processed: int
    insights_count: int
    themes_count: int
    errors_count: int
    has_checkpoint: bool
    latest_checkpoint_at: datetime | None = None
    phases_completed: list[str]
    current_phase: str | None = None


class ResumeJobRequest(BaseModel):
    """Request to resume a job from checkpoint."""

    from_checkpoint: bool = True  # If false, restart from beginning
