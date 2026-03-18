"""Celery tasks."""

from app.worker.tasks.documents import (
    process_document_task,
    embed_document_task,
    summarize_document_task,
)
from app.worker.tasks.research import (
    run_research_job,
    search_and_collect_task,
    process_collection_task,
)

__all__ = [
    "process_document_task",
    "embed_document_task",
    "summarize_document_task",
    "run_research_job",
    "search_and_collect_task",
    "process_collection_task",
]
