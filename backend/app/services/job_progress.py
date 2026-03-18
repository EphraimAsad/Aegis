"""Service for managing job progress logs (agent memory)."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.job_progress_log import JobProgressLog, LogEntryType


class JobProgressService:
    """
    Service for job progress log operations.

    Supports both sync (for Celery tasks) and async (for API) contexts.
    """

    def __init__(self, db: AsyncSession | Session) -> None:
        """Initialize with database session."""
        self.db = db
        self._is_async = isinstance(db, AsyncSession)

    def _get_next_sequence_sync(self, job_id: int) -> int:
        """Get the next sequence number for a job (sync)."""
        result = self.db.execute(
            select(func.coalesce(func.max(JobProgressLog.sequence), 0))
            .where(JobProgressLog.job_id == job_id)
        )
        return (result.scalar() or 0) + 1

    async def _get_next_sequence_async(self, job_id: int) -> int:
        """Get the next sequence number for a job (async)."""
        result = await self.db.execute(
            select(func.coalesce(func.max(JobProgressLog.sequence), 0))
            .where(JobProgressLog.job_id == job_id)
        )
        return (result.scalar() or 0) + 1

    def log_sync(
        self,
        job_id: int,
        entry_type: LogEntryType,
        message: str,
        phase: str | None = None,
        data: dict | None = None,
        is_checkpoint: bool = False,
        checkpoint_state: dict | None = None,
    ) -> JobProgressLog:
        """
        Create a progress log entry (synchronous for Celery).

        Args:
            job_id: Job ID
            entry_type: Type of log entry
            message: Human-readable message
            phase: Current workflow phase
            data: Structured data for the entry
            is_checkpoint: Whether this is a resumable checkpoint
            checkpoint_state: State needed for resumption

        Returns:
            Created log entry
        """
        sequence = self._get_next_sequence_sync(job_id)

        entry = JobProgressLog(
            job_id=job_id,
            entry_type=entry_type,
            phase=phase,
            message=message,
            data=data,
            is_checkpoint=is_checkpoint,
            checkpoint_state=checkpoint_state,
            sequence=sequence,
        )

        self.db.add(entry)
        self.db.flush()

        return entry

    async def log_async(
        self,
        job_id: int,
        entry_type: LogEntryType,
        message: str,
        phase: str | None = None,
        data: dict | None = None,
        is_checkpoint: bool = False,
        checkpoint_state: dict | None = None,
    ) -> JobProgressLog:
        """
        Create a progress log entry (async for API).

        Args:
            job_id: Job ID
            entry_type: Type of log entry
            message: Human-readable message
            phase: Current workflow phase
            data: Structured data for the entry
            is_checkpoint: Whether this is a resumable checkpoint
            checkpoint_state: State needed for resumption

        Returns:
            Created log entry
        """
        sequence = await self._get_next_sequence_async(job_id)

        entry = JobProgressLog(
            job_id=job_id,
            entry_type=entry_type,
            phase=phase,
            message=message,
            data=data,
            is_checkpoint=is_checkpoint,
            checkpoint_state=checkpoint_state,
            sequence=sequence,
        )

        self.db.add(entry)
        await self.db.flush()

        return entry

    # Convenience methods for common log types (sync versions for Celery)

    def log_phase_start(
        self,
        job_id: int,
        phase: str,
        message: str | None = None,
        data: dict | None = None,
    ) -> JobProgressLog:
        """Log the start of a workflow phase."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.PHASE_START,
            phase=phase,
            message=message or f"Starting phase: {phase}",
            data=data,
        )

    def log_phase_complete(
        self,
        job_id: int,
        phase: str,
        message: str | None = None,
        data: dict | None = None,
    ) -> JobProgressLog:
        """Log the completion of a workflow phase."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.PHASE_COMPLETE,
            phase=phase,
            message=message or f"Completed phase: {phase}",
            data=data,
        )

    def log_paper_found(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log a paper discovery."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.PAPER_FOUND,
            phase=phase or "search",
            message=message,
            data=data,
        )

    def log_paper_collected(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log a paper being added to collection."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.PAPER_COLLECTED,
            phase=phase or "collect",
            message=message,
            data=data,
        )

    def log_paper_processed(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log a paper being processed."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.PAPER_PROCESSED,
            phase=phase or "process",
            message=message,
            data=data,
        )

    def log_insight(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log a discovered insight."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.INSIGHT,
            phase=phase or "synthesis",
            message=message,
            data=data,
        )

    def log_theme(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log an identified theme."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.THEME,
            phase=phase or "synthesis",
            message=message,
            data=data,
        )

    def create_checkpoint(
        self,
        job_id: int,
        current_step: int,
        step_name: str,
        items_processed: list[int] | None = None,
        items_remaining: list[int] | None = None,
        accumulated_results: dict | None = None,
        search_cursors: dict[str, str] | None = None,
        context_summary: str | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """
        Create a resumable checkpoint.

        This captures all state needed to resume the job from this point.

        Args:
            job_id: Job ID
            current_step: Step number
            step_name: Name of current step
            items_processed: IDs of items already processed
            items_remaining: IDs of items still to process
            accumulated_results: Partial results to preserve
            search_cursors: Pagination cursors for sources
            context_summary: Summary of work done (for agent memory)
            phase: Current phase (optional)

        Returns:
            Checkpoint log entry
        """
        checkpoint_state = {
            "current_step": current_step,
            "step_name": step_name,
            "items_processed": items_processed or [],
            "items_remaining": items_remaining or [],
            "search_cursors": search_cursors or {},
            "accumulated_results": accumulated_results or {},
            "context_summary": context_summary,
            "checkpoint_time": datetime.utcnow().isoformat(),
        }

        processed_count = len(items_processed) if items_processed else 0
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.CHECKPOINT,
            phase=phase or step_name,
            message=f"Checkpoint: {step_name} ({processed_count} items processed)",
            data={"step": current_step, "step_name": step_name},
            is_checkpoint=True,
            checkpoint_state=checkpoint_state,
        )

    def log_error(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log an error (potentially recoverable)."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.ERROR,
            phase=phase or "error",
            message=message,
            data=data,
        )

    def log_recovery(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log recovery from error or checkpoint."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.RECOVERY,
            phase=phase or "recovery",
            message=message,
            data=data,
        )

    def log_api_call(
        self,
        job_id: int,
        message: str,
        data: dict | None = None,
        phase: str | None = None,
    ) -> JobProgressLog:
        """Log an API call for resource tracking."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.API_CALL,
            phase=phase or "api",
            message=message,
            data=data,
        )

    def log_info(
        self,
        job_id: int,
        message: str,
        phase: str | None = None,
        data: dict | None = None,
    ) -> JobProgressLog:
        """Log general information."""
        return self.log_sync(
            job_id=job_id,
            entry_type=LogEntryType.INFO,
            phase=phase,
            message=message,
            data=data,
        )

    # Query methods (sync versions)

    def get_latest_checkpoint_sync(self, job_id: int) -> JobProgressLog | None:
        """Get the most recent checkpoint for a job (sync)."""
        result = self.db.execute(
            select(JobProgressLog)
            .where(JobProgressLog.job_id == job_id)
            .where(JobProgressLog.is_checkpoint == True)
            .order_by(JobProgressLog.sequence.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def get_entries_sync(
        self,
        job_id: int,
        entry_type: LogEntryType | None = None,
        phase: str | None = None,
        checkpoints_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobProgressLog]:
        """Get log entries for a job (sync)."""
        query = select(JobProgressLog).where(JobProgressLog.job_id == job_id)

        if entry_type:
            query = query.where(JobProgressLog.entry_type == entry_type)
        if phase:
            query = query.where(JobProgressLog.phase == phase)
        if checkpoints_only:
            query = query.where(JobProgressLog.is_checkpoint == True)

        query = query.order_by(JobProgressLog.sequence.asc())
        query = query.offset(offset).limit(limit)

        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_progress_summary_sync(self, job_id: int) -> dict:
        """Get a summary of job progress (sync)."""
        entries = self.db.execute(
            select(JobProgressLog).where(JobProgressLog.job_id == job_id)
        ).scalars().all()

        summary = {
            "job_id": job_id,
            "total_entries": len(entries),
            "papers_found": 0,
            "papers_collected": 0,
            "papers_processed": 0,
            "insights_count": 0,
            "themes_count": 0,
            "errors_count": 0,
            "has_checkpoint": False,
            "latest_checkpoint_at": None,
            "phases_completed": [],
            "current_phase": None,
        }

        for entry in entries:
            if entry.entry_type == LogEntryType.PAPER_FOUND:
                summary["papers_found"] += 1
            elif entry.entry_type == LogEntryType.PAPER_COLLECTED:
                summary["papers_collected"] += 1
            elif entry.entry_type == LogEntryType.PAPER_PROCESSED:
                summary["papers_processed"] += 1
            elif entry.entry_type == LogEntryType.INSIGHT:
                summary["insights_count"] += 1
            elif entry.entry_type == LogEntryType.THEME:
                summary["themes_count"] += 1
            elif entry.entry_type == LogEntryType.ERROR:
                summary["errors_count"] += 1
            elif entry.entry_type == LogEntryType.CHECKPOINT:
                summary["has_checkpoint"] = True
                summary["latest_checkpoint_at"] = entry.created_at
            elif entry.entry_type == LogEntryType.PHASE_START:
                summary["current_phase"] = entry.phase
            elif entry.entry_type == LogEntryType.PHASE_COMPLETE:
                if entry.phase and entry.phase not in summary["phases_completed"]:
                    summary["phases_completed"].append(entry.phase)

        return summary

    # Query methods (async versions for API)

    async def get_latest_checkpoint(self, job_id: int) -> JobProgressLog | None:
        """Get the most recent checkpoint for a job (async)."""
        result = await self.db.execute(
            select(JobProgressLog)
            .where(JobProgressLog.job_id == job_id)
            .where(JobProgressLog.is_checkpoint == True)
            .order_by(JobProgressLog.sequence.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_entries(
        self,
        job_id: int,
        entry_type: LogEntryType | None = None,
        phase: str | None = None,
        checkpoints_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[JobProgressLog]:
        """Get log entries for a job with optional filters (async)."""
        query = select(JobProgressLog).where(JobProgressLog.job_id == job_id)

        if entry_type:
            query = query.where(JobProgressLog.entry_type == entry_type)
        if phase:
            query = query.where(JobProgressLog.phase == phase)
        if checkpoints_only:
            query = query.where(JobProgressLog.is_checkpoint == True)

        query = query.order_by(JobProgressLog.sequence.asc())

        if offset > 0:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_progress_summary(self, job_id: int) -> dict:
        """Get a summary of job progress (async)."""
        result = await self.db.execute(
            select(JobProgressLog).where(JobProgressLog.job_id == job_id)
        )
        entries = result.scalars().all()

        summary = {
            "job_id": job_id,
            "total_entries": len(entries),
            "papers_found": 0,
            "papers_collected": 0,
            "papers_processed": 0,
            "insights_count": 0,
            "themes_count": 0,
            "errors_count": 0,
            "has_checkpoint": False,
            "latest_checkpoint_at": None,
            "phases_completed": [],
            "current_phase": None,
        }

        for entry in entries:
            if entry.entry_type == LogEntryType.PAPER_FOUND:
                summary["papers_found"] += 1
            elif entry.entry_type == LogEntryType.PAPER_COLLECTED:
                summary["papers_collected"] += 1
            elif entry.entry_type == LogEntryType.PAPER_PROCESSED:
                summary["papers_processed"] += 1
            elif entry.entry_type == LogEntryType.INSIGHT:
                summary["insights_count"] += 1
            elif entry.entry_type == LogEntryType.THEME:
                summary["themes_count"] += 1
            elif entry.entry_type == LogEntryType.ERROR:
                summary["errors_count"] += 1
            elif entry.entry_type == LogEntryType.CHECKPOINT:
                summary["has_checkpoint"] = True
                summary["latest_checkpoint_at"] = entry.created_at
            elif entry.entry_type == LogEntryType.PHASE_START:
                summary["current_phase"] = entry.phase
            elif entry.entry_type == LogEntryType.PHASE_COMPLETE:
                if entry.phase and entry.phase not in summary["phases_completed"]:
                    summary["phases_completed"].append(entry.phase)

        return summary


def get_job_progress_service(db: AsyncSession | Session) -> JobProgressService:
    """Get a job progress service instance."""
    return JobProgressService(db)
