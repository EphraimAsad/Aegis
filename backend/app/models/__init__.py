"""SQLAlchemy models.

Import all models here to ensure they are registered with the Base metadata.
This is necessary for Alembic to detect them for migrations.
"""

from app.db.base import Base
from app.models.clarification import (
    ClarificationQuestion,
    QuestionCategory,
    QuestionType,
)
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.job import Job, JobPriority, JobStatus, JobType
from app.models.job_progress_log import JobProgressLog, LogEntryType
from app.models.project import Project, ProjectStatus

__all__ = [
    "Base",
    "Project",
    "ProjectStatus",
    "ClarificationQuestion",
    "QuestionType",
    "QuestionCategory",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "Job",
    "JobType",
    "JobStatus",
    "JobPriority",
    "JobProgressLog",
    "LogEntryType",
]
