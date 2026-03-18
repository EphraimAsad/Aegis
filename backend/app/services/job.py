"""Job service for managing background tasks."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.job import Job, JobPriority, JobStatus, JobType
from app.schemas.job import ResearchJobConfig


class JobService:
    """Service for job operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    async def create(
        self,
        job_type: JobType,
        name: str,
        description: str | None = None,
        project_id: int | None = None,
        priority: JobPriority = JobPriority.NORMAL,
        input_data: dict | None = None,
        parent_job_id: int | None = None,
        total_steps: int = 1,
        items_total: int = 0,
    ) -> Job:
        """
        Create a new job.

        Args:
            job_type: Type of job
            name: Job name
            description: Optional description
            project_id: Associated project
            priority: Job priority
            input_data: Input configuration
            parent_job_id: Parent job for sub-tasks
            total_steps: Total steps in job
            items_total: Total items to process

        Returns:
            Created job
        """
        job = Job(
            job_type=job_type,
            name=name,
            description=description,
            project_id=project_id,
            priority=priority,
            input_data=input_data,
            parent_job_id=parent_job_id,
            total_steps=total_steps,
            items_total=items_total,
            status=JobStatus.PENDING,
        )

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def get(self, job_id: int) -> Job:
        """
        Get a job by ID.

        Args:
            job_id: Job ID

        Returns:
            The job

        Raises:
            NotFoundError: If job not found
        """
        result = await self.db.execute(
            select(Job).options(selectinload(Job.child_jobs)).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise NotFoundError(
                f"Job with id {job_id} not found",
                details={"job_id": job_id},
            )

        return job

    async def get_by_celery_id(self, celery_task_id: str) -> Job | None:
        """
        Get a job by its Celery task ID.

        Args:
            celery_task_id: Celery task ID

        Returns:
            The job or None
        """
        result = await self.db.execute(
            select(Job).where(Job.celery_task_id == celery_task_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id: int | None = None,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        """
        List jobs with pagination.

        Args:
            project_id: Filter by project
            status: Filter by status
            job_type: Filter by type
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (jobs, total_count)
        """
        query = select(Job)

        if project_id is not None:
            query = query.where(Job.project_id == project_id)
        if status is not None:
            query = query.where(Job.status == status)
        if job_type is not None:
            query = query.where(Job.job_type == job_type)

        # Count total
        count_query = select(func.count(Job.id))
        if project_id is not None:
            count_query = count_query.where(Job.project_id == project_id)
        if status is not None:
            count_query = count_query.where(Job.status == status)
        if job_type is not None:
            count_query = count_query.where(Job.job_type == job_type)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Job.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        return jobs, total

    async def update_status(
        self,
        job_id: int,
        status: JobStatus,
        error_message: str | None = None,
        result_data: dict | None = None,
    ) -> Job:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            error_message: Error message if failed
            result_data: Result data if completed

        Returns:
            Updated job
        """
        job = await self.get(job_id)

        job.status = status

        if status == JobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()

        if error_message:
            job.error_message = error_message
        if result_data:
            job.result_data = result_data

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def update_progress(
        self,
        job_id: int,
        progress: float | None = None,
        message: str | None = None,
        current_step: int | None = None,
        items_processed: int | None = None,
    ) -> Job:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress value (0.0-1.0)
            message: Progress message
            current_step: Current step number
            items_processed: Items processed count

        Returns:
            Updated job
        """
        job = await self.get(job_id)
        job.update_progress(progress, message, current_step, items_processed)

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def cancel(self, job_id: int) -> Job:
        """
        Cancel a job.

        Args:
            job_id: Job ID

        Returns:
            Cancelled job

        Raises:
            ValidationError: If job cannot be cancelled
        """
        job = await self.get(job_id)

        if job.is_finished:
            raise ValidationError(
                f"Cannot cancel job in {job.status} status",
                details={"status": job.status},
            )

        # Cancel in Celery
        if job.celery_task_id:
            from app.worker.celery_app import celery_app

            celery_app.control.revoke(job.celery_task_id, terminate=True)

        job.mark_cancelled()

        await self.db.flush()
        await self.db.refresh(job)

        return job

    async def retry(self, job_id: int) -> Job:
        """
        Retry a failed job.

        Args:
            job_id: Job ID

        Returns:
            New job for retry

        Raises:
            ValidationError: If job cannot be retried
        """
        job = await self.get(job_id)

        if job.status != JobStatus.FAILED:
            raise ValidationError(
                f"Cannot retry job in {job.status} status",
                details={"status": job.status},
            )

        if job.retry_count >= job.max_retries:
            raise ValidationError(
                "Maximum retries exceeded",
                details={
                    "retry_count": job.retry_count,
                    "max_retries": job.max_retries,
                },
            )

        # Create new job as retry
        new_job = Job(
            job_type=job.job_type,
            name=f"{job.name} (retry {job.retry_count + 1})",
            description=job.description,
            project_id=job.project_id,
            priority=job.priority,
            input_data=job.input_data,
            parent_job_id=job.parent_job_id,
            total_steps=job.total_steps,
            items_total=job.items_total,
            retry_count=job.retry_count + 1,
            max_retries=job.max_retries,
            status=JobStatus.PENDING,
        )

        self.db.add(new_job)
        await self.db.flush()
        await self.db.refresh(new_job)

        return new_job

    async def get_stats(self, project_id: int | None = None) -> dict:
        """
        Get job statistics.

        Args:
            project_id: Optional project filter

        Returns:
            Statistics dict
        """
        base_query = select(Job)
        if project_id is not None:
            base_query = base_query.where(Job.project_id == project_id)

        # Count by status
        status_counts = {}
        for status in JobStatus:
            query = select(func.count(Job.id)).where(Job.status == status)
            if project_id is not None:
                query = query.where(Job.project_id == project_id)
            result = await self.db.execute(query)
            status_counts[status.value] = result.scalar() or 0

        # Count by type
        type_counts = {}
        for job_type in JobType:
            query = select(func.count(Job.id)).where(Job.job_type == job_type)
            if project_id is not None:
                query = query.where(Job.project_id == project_id)
            result = await self.db.execute(query)
            type_counts[job_type.value] = result.scalar() or 0

        # Average duration
        avg_query = select(
            func.avg(
                func.extract("epoch", Job.completed_at)
                - func.extract("epoch", Job.started_at)
            )
        ).where(
            Job.status == JobStatus.COMPLETED,
            Job.started_at.isnot(None),
            Job.completed_at.isnot(None),
        )
        if project_id is not None:
            avg_query = avg_query.where(Job.project_id == project_id)
        avg_result = await self.db.execute(avg_query)
        avg_duration = avg_result.scalar()

        # Total tokens
        tokens_query = select(func.sum(Job.tokens_used))
        if project_id is not None:
            tokens_query = tokens_query.where(Job.project_id == project_id)
        tokens_result = await self.db.execute(tokens_query)
        total_tokens = tokens_result.scalar() or 0

        # Jobs last 24h
        yesterday = datetime.utcnow() - timedelta(days=1)
        last_24h_query = select(func.count(Job.id)).where(Job.created_at >= yesterday)
        if project_id is not None:
            last_24h_query = last_24h_query.where(Job.project_id == project_id)
        last_24h_result = await self.db.execute(last_24h_query)
        jobs_last_24h = last_24h_result.scalar() or 0

        # Jobs last 7d
        last_week = datetime.utcnow() - timedelta(days=7)
        last_7d_query = select(func.count(Job.id)).where(Job.created_at >= last_week)
        if project_id is not None:
            last_7d_query = last_7d_query.where(Job.project_id == project_id)
        last_7d_result = await self.db.execute(last_7d_query)
        jobs_last_7d = last_7d_result.scalar() or 0

        return {
            "total_jobs": sum(status_counts.values()),
            "by_status": status_counts,
            "by_type": type_counts,
            "avg_duration_seconds": float(avg_duration) if avg_duration else None,
            "total_tokens_used": total_tokens,
            "jobs_last_24h": jobs_last_24h,
            "jobs_last_7d": jobs_last_7d,
        }

    async def start_research_job(
        self,
        project_id: int,
        config: ResearchJobConfig,
        name: str | None = None,
        description: str | None = None,
        priority: JobPriority = JobPriority.NORMAL,
    ) -> Job:
        """
        Start a full research job.

        Args:
            project_id: Project to research
            config: Research configuration
            name: Optional job name
            description: Optional description
            priority: Job priority

        Returns:
            Created job
        """
        from app.worker.tasks.research import run_research_job

        # Create job record
        job = await self.create(
            job_type=JobType.RESEARCH_FULL,
            name=name or f"Research job for project {project_id}",
            description=description,
            project_id=project_id,
            priority=priority,
            input_data=config.model_dump(),
            total_steps=5,
        )

        await self.db.commit()

        # Start Celery task
        task = run_research_job.delay(
            job_id=job.id,
            project_id=project_id,
            config=config.model_dump(),
        )

        # Update with task ID
        job.celery_task_id = task.id
        await self.db.commit()

        return job

    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Clean up old completed/failed jobs.

        Args:
            days: Keep jobs newer than this

        Returns:
            Number of jobs deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(Job)
            .where(
                Job.status.in_(
                    [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
                )
            )
            .where(Job.completed_at < cutoff)
        )
        old_jobs = list(result.scalars().all())

        for job in old_jobs:
            await self.db.delete(job)

        await self.db.flush()

        return len(old_jobs)


def get_job_service(db: AsyncSession) -> JobService:
    """Get a job service instance."""
    return JobService(db)
