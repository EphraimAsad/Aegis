"""Celery tasks for research workflow."""

import traceback
from datetime import datetime

from celery import chain, chord, group, shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.document import Document, DocumentStatus
from app.models.job import Job, JobStatus, JobType
from app.models.project import Project, ProjectStatus


def get_db_session() -> Session:
    """Get a synchronous database session for Celery tasks."""
    return next(get_sync_session())


@shared_task(bind=True, name="app.worker.tasks.research.run_research_job")
def run_research_job(
    self,
    job_id: int,
    project_id: int,
    config: dict,
) -> dict:
    """
    Run a full research job for a project.

    This orchestrates the complete research workflow:
    1. Search academic sources based on project scope
    2. Collect and deduplicate papers
    3. Process documents (chunk, embed, summarize)
    4. Generate synthesis and insights

    Args:
        job_id: Job ID for tracking
        project_id: Project to research
        config: Research configuration dict

    Returns:
        Research results dict
    """
    db = get_db_session()

    try:
        # Get job and project
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        project = db.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()

        if not job or not project:
            raise ValueError(f"Job {job_id} or Project {project_id} not found")

        job.celery_task_id = self.request.id
        job.mark_started()
        job.total_steps = 5
        job.progress_message = "Starting research job..."
        db.commit()

        result = {
            "project_id": project_id,
            "papers_found": 0,
            "papers_collected": 0,
            "papers_processed": 0,
            "papers_failed": 0,
            "synthesis_generated": False,
            "themes_identified": [],
            "errors": [],
        }

        # Step 1: Build search query from project scope
        job.update_progress(current_step=1, message="Building search query...")
        db.commit()

        scope = project.scope or {}
        keywords = scope.get("keywords", [])
        if not keywords and project.research_objective:
            # Extract keywords from objective
            keywords = project.research_objective.split()[:5]

        search_query = " ".join(keywords[:10])

        # Step 2: Search sources
        job.update_progress(current_step=2, message="Searching academic sources...")
        db.commit()

        # This would call source adapters
        # Simplified for sync context
        max_per_source = config.get("max_papers_per_source", 100)
        sources = config.get("sources") or ["openalex", "crossref", "semantic_scholar"]

        # Placeholder for search results
        papers_found = 0
        for source in sources:
            # In production, call source adapter
            papers_found += 10  # Placeholder

        result["papers_found"] = papers_found

        # Step 3: Collect and add papers
        job.update_progress(current_step=3, message="Collecting papers...")
        db.commit()

        # Papers would be added to documents
        papers_collected = min(papers_found, max_per_source * len(sources))
        result["papers_collected"] = papers_collected
        job.items_total = papers_collected

        # Step 4: Process documents
        if config.get("process_documents", True):
            job.update_progress(current_step=4, message="Processing documents...")
            db.commit()

            # Get pending documents
            pending_docs = db.execute(
                select(Document)
                .where(Document.project_id == project_id)
                .where(Document.status == DocumentStatus.PENDING)
            ).scalars().all()

            processed = 0
            failed = 0

            for doc in pending_docs:
                try:
                    # Simplified processing
                    doc.status = DocumentStatus.READY
                    processed += 1
                    job.items_processed = processed
                    db.commit()
                except Exception as e:
                    doc.status = DocumentStatus.ERROR
                    doc.error_message = str(e)
                    failed += 1
                    result["errors"].append({
                        "document_id": doc.id,
                        "error": str(e),
                    })
                    db.commit()

            result["papers_processed"] = processed
            result["papers_failed"] = failed

        # Step 5: Generate synthesis
        if config.get("generate_synthesis", True):
            job.update_progress(current_step=5, message="Generating synthesis...")
            db.commit()

            # Would call summarization service
            result["synthesis_generated"] = True

        # Identify themes
        if config.get("identify_themes", True):
            # Would analyze collected papers
            result["themes_identified"] = [
                "Theme 1",
                "Theme 2",
            ]

        # Update project status
        project.status = ProjectStatus.ACTIVE

        # Mark job complete
        job.mark_completed(result)
        db.commit()

        return result

    except Exception as e:
        if job:
            job.mark_failed(str(e), traceback.format_exc())
            db.commit()
        raise

    finally:
        db.close()


@shared_task(bind=True, name="app.worker.tasks.research.search_and_collect")
def search_and_collect_task(
    self,
    job_id: int,
    project_id: int,
    query: str,
    sources: list[str] | None = None,
    max_per_source: int = 100,
) -> dict:
    """
    Search sources and collect papers.

    Args:
        job_id: Job ID for tracking
        project_id: Project to add papers to
        query: Search query
        sources: Sources to search
        max_per_source: Max papers per source

    Returns:
        Collection results
    """
    db = get_db_session()

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            db.commit()

        sources = sources or ["openalex", "crossref", "semantic_scholar", "arxiv", "pubmed"]

        result = {
            "query": query,
            "sources_searched": sources,
            "papers_found": {},
            "papers_added": 0,
            "papers_skipped": 0,
            "errors": [],
        }

        total_found = 0
        for source in sources:
            # Would call source adapter here
            # Placeholder
            found = 10
            result["papers_found"][source] = found
            total_found += found

        job.items_total = total_found

        # Would add papers as documents
        result["papers_added"] = total_found
        job.items_processed = total_found

        if job:
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        if job:
            job.mark_failed(str(e), traceback.format_exc())
            db.commit()
        raise

    finally:
        db.close()


@shared_task(bind=True, name="app.worker.tasks.research.process_collection")
def process_collection_task(
    self,
    job_id: int,
    project_id: int,
    generate_summaries: bool = True,
    extract_evidence: bool = True,
    auto_tag: bool = True,
) -> dict:
    """
    Process all documents in a project's collection.

    Args:
        job_id: Job ID for tracking
        project_id: Project with documents
        generate_summaries: Whether to generate summaries
        extract_evidence: Whether to extract evidence
        auto_tag: Whether to auto-tag

    Returns:
        Processing results
    """
    db = get_db_session()

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            db.commit()

        # Get pending documents
        documents = db.execute(
            select(Document)
            .where(Document.project_id == project_id)
            .where(Document.status.in_([DocumentStatus.PENDING, DocumentStatus.ERROR]))
        ).scalars().all()

        job.items_total = len(documents)
        db.commit()

        result = {
            "project_id": project_id,
            "total_documents": len(documents),
            "processed": 0,
            "failed": 0,
            "errors": [],
        }

        for i, doc in enumerate(documents):
            try:
                doc.status = DocumentStatus.PROCESSING
                db.commit()

                # Would call processing services
                doc.status = DocumentStatus.READY
                result["processed"] += 1

                job.update_progress(
                    items_processed=result["processed"],
                    message=f"Processed {result['processed']}/{len(documents)}",
                )
                db.commit()

            except Exception as e:
                doc.status = DocumentStatus.ERROR
                doc.error_message = str(e)
                result["failed"] += 1
                result["errors"].append({
                    "document_id": doc.id,
                    "error": str(e),
                })
                db.commit()

        if job:
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        if job:
            job.mark_failed(str(e), traceback.format_exc())
            db.commit()
        raise

    finally:
        db.close()


@shared_task(bind=True, name="app.worker.tasks.research.generate_synthesis")
def generate_synthesis_task(
    self,
    job_id: int,
    project_id: int,
) -> dict:
    """
    Generate a synthesis of the research findings.

    Args:
        job_id: Job ID for tracking
        project_id: Project to synthesize

    Returns:
        Synthesis results
    """
    db = get_db_session()

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            db.commit()

        # Get processed documents
        documents = db.execute(
            select(Document)
            .where(Document.project_id == project_id)
            .where(Document.status == DocumentStatus.READY)
        ).scalars().all()

        result = {
            "project_id": project_id,
            "documents_analyzed": len(documents),
            "synthesis": None,
            "themes": [],
            "key_findings": [],
            "gaps": [],
        }

        if not documents:
            if job:
                job.mark_completed(result)
                db.commit()
            return result

        job.update_progress(progress=0.3, message="Analyzing documents...")
        db.commit()

        # Would call summarization service for comparative analysis
        # Placeholder
        result["synthesis"] = "Research synthesis placeholder..."
        result["themes"] = [
            {"name": "Theme 1", "document_count": len(documents) // 2},
            {"name": "Theme 2", "document_count": len(documents) // 2},
        ]
        result["key_findings"] = [
            "Key finding 1",
            "Key finding 2",
        ]
        result["gaps"] = [
            "Research gap 1",
        ]

        if job:
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        if job:
            job.mark_failed(str(e), traceback.format_exc())
            db.commit()
        raise

    finally:
        db.close()
