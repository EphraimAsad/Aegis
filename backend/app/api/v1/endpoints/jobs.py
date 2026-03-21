"""Job management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job import JobPriority as ModelJobPriority
from app.models.job import JobStatus, JobType
from app.models.job_progress_log import LogEntryType as ModelLogEntryType
from app.schemas.job import (
    BatchProcessRequest,
    BatchProcessResponse,
    JobDetail,
    JobListResponse,
    JobStatsResponse,
    JobSummary,
    StartResearchJobRequest,
    StartResearchJobResponse,
)
from app.schemas.job_progress import (
    JobProgressSummary,
    LogEntryType,
    ProgressLogEntry,
    ProgressLogList,
    ResumeJobRequest,
)
from app.services.job import JobService
from app.services.job_progress import JobProgressService

router = APIRouter()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    project_id: int | None = None,
    status: JobStatus | None = None,
    job_type: JobType | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    List jobs with optional filters.

    Filter by project, status, or job type.
    """
    service = JobService(db)
    jobs, total = await service.list(
        project_id=project_id,
        status=status,
        job_type=job_type,
        page=page,
        page_size=page_size,
    )

    summaries = [
        JobSummary(
            id=job.id,
            job_type=job.job_type,
            name=job.name,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            progress_message=job.progress_message,
            project_id=job.project_id,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]

    return JobListResponse(
        jobs=summaries,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/stats", response_model=JobStatsResponse)
async def get_job_stats(
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> JobStatsResponse:
    """
    Get job statistics.

    Returns counts by status, type, and recent activity.
    """
    service = JobService(db)
    stats = await service.get_stats(project_id)
    return JobStatsResponse(**stats)


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobDetail:
    """
    Get job details by ID.

    Returns full job information including progress and results.
    """
    service = JobService(db)
    try:
        job = await service.get(job_id)
        return JobDetail(
            id=job.id,
            celery_task_id=job.celery_task_id,
            job_type=job.job_type,
            name=job.name,
            description=job.description,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            progress_message=job.progress_message,
            current_step=job.current_step,
            total_steps=job.total_steps,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_completion=job.estimated_completion,
            duration_seconds=job.duration_seconds,
            result_data=job.result_data,
            error_message=job.error_message,
            items_processed=job.items_processed,
            items_total=job.items_total,
            items_failed=job.items_failed,
            tokens_used=job.tokens_used,
            api_calls_made=job.api_calls_made,
            project_id=job.project_id,
            parent_job_id=job.parent_job_id,
            child_job_count=len(job.child_jobs) if job.child_jobs else 0,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{job_id}/cancel", response_model=JobDetail)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobDetail:
    """
    Cancel a running or pending job.

    Terminates the Celery task and marks the job as cancelled.
    """
    service = JobService(db)
    try:
        job = await service.cancel(job_id)
        await db.commit()
        return JobDetail(
            id=job.id,
            celery_task_id=job.celery_task_id,
            job_type=job.job_type,
            name=job.name,
            description=job.description,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            progress_message=job.progress_message,
            current_step=job.current_step,
            total_steps=job.total_steps,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_completion=job.estimated_completion,
            duration_seconds=job.duration_seconds,
            result_data=job.result_data,
            error_message=job.error_message,
            items_processed=job.items_processed,
            items_total=job.items_total,
            items_failed=job.items_failed,
            tokens_used=job.tokens_used,
            api_calls_made=job.api_calls_made,
            project_id=job.project_id,
            parent_job_id=job.parent_job_id,
            child_job_count=len(job.child_jobs) if job.child_jobs else 0,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/{job_id}/retry", response_model=JobDetail)
async def retry_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobDetail:
    """
    Retry a failed job.

    Creates a new job with the same configuration.
    """
    service = JobService(db)
    try:
        job = await service.retry(job_id)
        await db.commit()

        # Re-submit to Celery based on job type
        if job.job_type == JobType.RESEARCH_FULL:
            from app.worker.tasks.research import run_research_job

            task = run_research_job.delay(
                job_id=job.id,
                project_id=job.project_id,
                config=job.input_data or {},
            )
            job.celery_task_id = task.id
            await db.commit()

        return JobDetail(
            id=job.id,
            celery_task_id=job.celery_task_id,
            job_type=job.job_type,
            name=job.name,
            description=job.description,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            progress_message=job.progress_message,
            current_step=job.current_step,
            total_steps=job.total_steps,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            estimated_completion=job.estimated_completion,
            duration_seconds=job.duration_seconds,
            result_data=job.result_data,
            error_message=job.error_message,
            items_processed=job.items_processed,
            items_total=job.items_total,
            items_failed=job.items_failed,
            tokens_used=job.tokens_used,
            api_calls_made=job.api_calls_made,
            project_id=job.project_id,
            parent_job_id=job.parent_job_id,
            child_job_count=0,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/research", response_model=StartResearchJobResponse)
async def start_research_job(
    request: StartResearchJobRequest,
    db: AsyncSession = Depends(get_db),
) -> StartResearchJobResponse:
    """
    Start a full research job for a project.

    This will:
    1. Search academic sources based on project scope
    2. Collect and deduplicate papers
    3. Process documents (chunk, embed, summarize)
    4. Generate synthesis and insights
    """
    service = JobService(db)

    try:
        job = await service.start_research_job(
            project_id=request.project_id,
            config=request.config,
            name=request.name,
            description=request.description,
            priority=ModelJobPriority(request.priority.value),
        )

        return StartResearchJobResponse(
            job_id=job.id,
            celery_task_id=job.celery_task_id,
            status=job.status,
            message=f"Research job started for project {request.project_id}",
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/batch-process", response_model=BatchProcessResponse)
async def start_batch_process(
    request: BatchProcessRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchProcessResponse:
    """
    Start batch processing of documents.

    Processes multiple documents in a project with specified operations.
    """
    from app.worker.tasks.documents import batch_process_task

    service = JobService(db)

    # Count documents to process
    from sqlalchemy import func, select

    from app.models.document import Document, DocumentStatus

    query = select(func.count(Document.id)).where(
        Document.project_id == request.project_id
    )
    if request.document_ids:
        query = query.where(Document.id.in_(request.document_ids))
    else:
        query = query.where(Document.status == DocumentStatus.PENDING)

    result = await db.execute(query)
    doc_count = result.scalar() or 0

    # Create job
    job = await service.create(
        job_type=JobType.BATCH_PROCESS,
        name=f"Batch process for project {request.project_id}",
        project_id=request.project_id,
        priority=ModelJobPriority(request.priority.value),
        input_data={
            "document_ids": request.document_ids,
            "operations": request.operations,
        },
        items_total=doc_count,
    )

    await db.commit()

    # Start Celery task
    task = batch_process_task.delay(
        job_id=job.id,
        project_id=request.project_id,
        document_ids=request.document_ids,
        operations=request.operations,
    )

    job.celery_task_id = task.id
    await db.commit()

    return BatchProcessResponse(
        job_id=job.id,
        documents_queued=doc_count,
        status=job.status,
    )


@router.get("/{job_id}/progress", response_model=ProgressLogList)
async def get_job_progress(
    job_id: int,
    entry_type: LogEntryType | None = None,
    phase: str | None = None,
    checkpoints_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ProgressLogList:
    """
    Get progress log entries for a job.

    Filter by entry type, phase, or get only checkpoints.
    """
    progress_service = JobProgressService(db)

    # Convert schema enum to model enum if provided
    model_entry_type = ModelLogEntryType(entry_type.value) if entry_type else None

    entries = await progress_service.get_entries(
        job_id=job_id,
        entry_type=model_entry_type,
        phase=phase,
        checkpoints_only=checkpoints_only,
        limit=page_size,
        offset=(page - 1) * page_size,
    )

    # Get total count
    all_entries = await progress_service.get_entries(
        job_id=job_id,
        entry_type=model_entry_type,
        phase=phase,
        checkpoints_only=checkpoints_only,
    )

    return ProgressLogList(
        entries=[
            ProgressLogEntry(
                id=e.id,
                job_id=e.job_id,
                entry_type=e.entry_type,
                phase=e.phase,
                message=e.message,
                data=e.data,
                is_checkpoint=e.is_checkpoint,
                sequence=e.sequence,
                created_at=e.created_at,
            )
            for e in entries
        ],
        total=len(all_entries),
        job_id=job_id,
    )


@router.get("/{job_id}/progress/summary", response_model=JobProgressSummary)
async def get_job_progress_summary(
    job_id: int,
    db: AsyncSession = Depends(get_db),
) -> JobProgressSummary:
    """
    Get aggregated progress summary for a job.

    Returns counts of papers found, collected, processed, insights, themes, etc.
    """
    progress_service = JobProgressService(db)

    try:
        summary = await progress_service.get_progress_summary(job_id)
        return JobProgressSummary(**summary)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{job_id}/resume", response_model=StartResearchJobResponse)
async def resume_job(
    job_id: int,
    request: ResumeJobRequest,
    db: AsyncSession = Depends(get_db),
) -> StartResearchJobResponse:
    """
    Resume a job from its last checkpoint.

    If from_checkpoint is False, restarts the job from the beginning.
    """
    job_service = JobService(db)
    progress_service = JobProgressService(db)

    try:
        job = await job_service.get(job_id)

        # Check if job can be resumed
        if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PAUSED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume job with status '{job.status}'. "
                f"Job must be failed, cancelled, or paused.",
            )

        # Check for checkpoint if resuming from checkpoint
        if request.from_checkpoint:
            checkpoint = await progress_service.get_latest_checkpoint(job_id)
            if not checkpoint:
                raise HTTPException(
                    status_code=400,
                    detail="No checkpoint found for this job. "
                    "Set from_checkpoint=false to restart from beginning.",
                )

        # Reset job status
        job.status = JobStatus.PENDING
        job.error_message = None
        job.error_traceback = None
        await db.commit()

        # Re-submit to Celery based on job type
        if job.job_type == JobType.RESEARCH_FULL:
            from app.worker.tasks.research import run_research_job

            task = run_research_job.delay(
                job_id=job.id,
                project_id=job.project_id,
                config=job.input_data or {},
                resume_from_checkpoint=request.from_checkpoint,
            )
            job.celery_task_id = task.id
            await db.commit()

            return StartResearchJobResponse(
                job_id=job.id,
                celery_task_id=task.id,
                status=JobStatus.PENDING,
                message=f"Job resumed {'from checkpoint' if request.from_checkpoint else 'from beginning'}",
            )

        elif job.job_type == JobType.SEARCH_COLLECT:
            from app.worker.tasks.research import search_and_collect_task

            input_data = job.input_data or {}
            task = search_and_collect_task.delay(
                job_id=job.id,
                project_id=job.project_id,
                query=input_data.get("query", ""),
                sources=input_data.get("sources"),
                max_per_source=input_data.get("max_per_source", 100),
                resume_from_checkpoint=request.from_checkpoint,
            )
            job.celery_task_id = task.id
            await db.commit()

            return StartResearchJobResponse(
                job_id=job.id,
                celery_task_id=task.id,
                status=JobStatus.PENDING,
                message="Search/collect job resumed",
            )

        elif job.job_type == JobType.ANALYZE_COLLECTION:
            from app.worker.tasks.research import process_collection_task

            input_data = job.input_data or {}
            task = process_collection_task.delay(
                job_id=job.id,
                project_id=job.project_id,
                generate_summaries=input_data.get("generate_summaries", True),
                extract_evidence=input_data.get("extract_evidence", True),
                auto_tag=input_data.get("auto_tag", True),
                resume_from_checkpoint=request.from_checkpoint,
            )
            job.celery_task_id = task.id
            await db.commit()

            return StartResearchJobResponse(
                job_id=job.id,
                celery_task_id=task.id,
                status=JobStatus.PENDING,
                message="Process collection job resumed",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Resume not supported for job type '{job.job_type}'",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/project/{project_id}/active")
async def get_active_jobs(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[JobSummary]:
    """
    Get active jobs for a project.

    Returns all pending and running jobs.
    """
    service = JobService(db)

    pending_jobs, _ = await service.list(
        project_id=project_id,
        status=JobStatus.PENDING,
        page_size=100,
    )

    running_jobs, _ = await service.list(
        project_id=project_id,
        status=JobStatus.RUNNING,
        page_size=100,
    )

    all_active = pending_jobs + running_jobs

    return [
        JobSummary(
            id=job.id,
            job_type=job.job_type,
            name=job.name,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            progress_message=job.progress_message,
            project_id=job.project_id,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        for job in all_active
    ]


@router.get("/project/{project_id}/history")
async def get_job_history(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """
    Get job history for a project.

    Returns all jobs ordered by creation date.
    """
    service = JobService(db)
    jobs, total = await service.list(
        project_id=project_id,
        page=page,
        page_size=page_size,
    )

    summaries = [
        JobSummary(
            id=job.id,
            job_type=job.job_type,
            name=job.name,
            status=job.status,
            priority=job.priority,
            progress=job.progress,
            progress_message=job.progress_message,
            project_id=job.project_id,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]

    return JobListResponse(
        jobs=summaries,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )
