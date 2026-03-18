"""Job schemas for API requests/responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Types of background jobs."""

    PROCESS_DOCUMENT = "process_document"
    EMBED_DOCUMENT = "embed_document"
    SUMMARIZE_DOCUMENT = "summarize_document"
    BATCH_PROCESS = "batch_process"
    RESEARCH_FULL = "research_full"
    SEARCH_COLLECT = "search_collect"
    ANALYZE_COLLECTION = "analyze_collection"
    CLEANUP = "cleanup"
    REINDEX = "reindex"


class JobStatus(str, Enum):
    """Job execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobPriority(str, Enum):
    """Job priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class JobCreate(BaseModel):
    """Schema for creating a job."""

    job_type: JobType
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    priority: JobPriority = JobPriority.NORMAL
    project_id: int | None = None
    input_data: dict | None = None


class JobProgress(BaseModel):
    """Schema for job progress updates."""

    progress: float = Field(..., ge=0.0, le=1.0)
    message: str | None = None
    current_step: int | None = None
    items_processed: int | None = None


class JobSummary(BaseModel):
    """Lightweight job summary for lists."""

    id: int
    job_type: JobType
    name: str
    status: JobStatus
    priority: JobPriority
    progress: float
    progress_message: str | None = None
    project_id: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobDetail(BaseModel):
    """Full job details."""

    id: int
    celery_task_id: str | None = None
    job_type: JobType
    name: str
    description: str | None = None
    status: JobStatus
    priority: JobPriority

    # Progress
    progress: float
    progress_message: str | None = None
    current_step: int
    total_steps: int

    # Timing
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_completion: datetime | None = None
    duration_seconds: float | None = None

    # Results
    result_data: dict | None = None
    error_message: str | None = None

    # Statistics
    items_processed: int
    items_total: int
    items_failed: int
    tokens_used: int
    api_calls_made: int

    # Relationships
    project_id: int | None = None
    parent_job_id: int | None = None
    child_job_count: int = 0

    # Retry
    retry_count: int
    max_retries: int

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: list[JobSummary]
    total: int
    page: int
    page_size: int
    has_more: bool


class JobStatsResponse(BaseModel):
    """Job statistics response."""

    total_jobs: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    avg_duration_seconds: float | None
    total_tokens_used: int
    jobs_last_24h: int
    jobs_last_7d: int


# Research job specific schemas

class ResearchJobConfig(BaseModel):
    """Configuration for a research job."""

    # Search settings
    max_papers_per_source: int = Field(100, ge=1, le=1000)
    sources: list[str] | None = None
    deduplicate: bool = True

    # Processing settings
    process_documents: bool = True
    generate_summaries: bool = True
    extract_evidence: bool = True
    auto_tag: bool = True

    # Chunking settings
    chunk_size: int = Field(1000, ge=100, le=5000)
    chunk_overlap: int = Field(200, ge=0, le=500)

    # Analysis settings
    generate_synthesis: bool = True
    identify_themes: bool = True

    # Resource limits
    max_api_calls: int = Field(1000, ge=1)
    max_tokens: int = Field(100000, ge=1)


class StartResearchJobRequest(BaseModel):
    """Request to start a full research job."""

    project_id: int
    name: str | None = None
    description: str | None = None
    priority: JobPriority = JobPriority.NORMAL
    config: ResearchJobConfig = Field(default_factory=ResearchJobConfig)


class StartResearchJobResponse(BaseModel):
    """Response from starting a research job."""

    job_id: int
    celery_task_id: str | None
    status: JobStatus
    message: str


class BatchProcessRequest(BaseModel):
    """Request to batch process documents."""

    project_id: int
    document_ids: list[int] | None = None  # None = all pending
    operations: list[str] = Field(
        default=["embed", "summarize", "tag"],
        description="Operations to perform: embed, summarize, tag, extract",
    )
    priority: JobPriority = JobPriority.NORMAL


class BatchProcessResponse(BaseModel):
    """Response from batch process request."""

    job_id: int
    documents_queued: int
    status: JobStatus
