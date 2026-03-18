"""Celery tasks for research workflow with progress logging and checkpointing."""

import traceback
from datetime import datetime
from typing import Any

from celery import chain, chord, group, shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.document import Document, DocumentStatus
from app.models.job import Job, JobStatus, JobType
from app.models.project import Project, ProjectStatus
from app.services.job_progress import JobProgressService


def get_db_session() -> Session:
    """Get a synchronous database session for Celery tasks."""
    return next(get_sync_session())


def _restore_from_checkpoint(checkpoint_state: dict) -> dict:
    """
    Restore task state from a checkpoint.

    Args:
        checkpoint_state: Saved checkpoint state

    Returns:
        Restored state dict
    """
    return {
        "current_step": checkpoint_state.get("current_step", 0),
        "step_name": checkpoint_state.get("step_name", ""),
        "items_processed": set(checkpoint_state.get("items_processed", [])),
        "items_remaining": checkpoint_state.get("items_remaining", []),
        "search_cursors": checkpoint_state.get("search_cursors", {}),
        "accumulated_results": checkpoint_state.get("accumulated_results", {}),
        "context_summary": checkpoint_state.get("context_summary", ""),
    }


@shared_task(bind=True, name="app.worker.tasks.research.run_research_job")
def run_research_job(
    self,
    job_id: int,
    project_id: int,
    config: dict,
    resume_from_checkpoint: bool = False,
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
        resume_from_checkpoint: Whether to resume from last checkpoint

    Returns:
        Research results dict
    """
    db = get_db_session()
    progress_service = JobProgressService(db)
    checkpoint_interval = config.get("checkpoint_interval", 10)

    try:
        # Get job and project
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        project = db.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()

        if not job or not project:
            raise ValueError(f"Job {job_id} or Project {project_id} not found")

        job.celery_task_id = self.request.id

        # Initialize result structure
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

        # Check for checkpoint to resume from
        restored_state = None
        start_step = 1

        if resume_from_checkpoint:
            checkpoint = progress_service.get_latest_checkpoint_sync(job_id)
            if checkpoint and checkpoint.checkpoint_state:
                restored_state = _restore_from_checkpoint(checkpoint.checkpoint_state)
                start_step = restored_state["current_step"]
                result.update(restored_state.get("accumulated_results", {}))

                progress_service.log_recovery(
                    job_id=job_id,
                    message=f"Resuming from checkpoint at step {start_step}: {restored_state['step_name']}",
                    data={
                        "checkpoint_step": start_step,
                        "items_already_processed": len(restored_state["items_processed"]),
                    },
                )
                job.status = JobStatus.RUNNING
                db.commit()
            else:
                # No checkpoint found, start fresh
                job.mark_started()
                progress_service.log_info(
                    job_id=job_id,
                    phase="init",
                    message="No checkpoint found, starting fresh",
                )
                db.commit()
        else:
            job.mark_started()
            db.commit()

        job.total_steps = 5
        job.progress_message = "Starting research job..."
        db.commit()

        # Log job start
        progress_service.log_phase_start(
            job_id=job_id,
            phase="research_job",
            message=f"Starting research job for project '{project.title}'",
            data={
                "project_id": project_id,
                "config": config,
                "resume_from_checkpoint": resume_from_checkpoint,
                "start_step": start_step,
            },
        )

        # Step 1: Build search query from project scope
        if start_step <= 1:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="build_query",
                message="Building search query from project scope",
            )

            job.update_progress(current_step=1, message="Building search query...")
            db.commit()

            scope = project.scope or {}
            keywords = scope.get("keywords", [])
            if not keywords and project.research_objective:
                # Extract keywords from objective
                keywords = project.research_objective.split()[:5]

            search_query = " ".join(keywords[:10])

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="build_query",
                message=f"Search query built: '{search_query}'",
                data={"query": search_query, "keywords": keywords},
            )

        # Step 2: Search sources
        if start_step <= 2:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="search_sources",
                message="Searching academic sources",
            )

            job.update_progress(current_step=2, message="Searching academic sources...")
            db.commit()

            max_per_source = config.get("max_papers_per_source", 100)
            sources = config.get("sources") or ["openalex", "crossref", "semantic_scholar"]

            # Get search cursors if resuming
            search_cursors = {}
            if restored_state:
                search_cursors = restored_state.get("search_cursors", {})

            papers_found = 0
            for source in sources:
                # Log API call
                progress_service.log_api_call(
                    job_id=job_id,
                    message=f"Searching {source}",
                    data={
                        "source": source,
                        "cursor": search_cursors.get(source),
                    },
                )

                # In production, call source adapter with cursor
                source_papers = 10  # Placeholder
                papers_found += source_papers

                # Log papers found from this source
                progress_service.log_paper_found(
                    job_id=job_id,
                    message=f"Found {source_papers} papers from {source}",
                    data={
                        "source": source,
                        "count": source_papers,
                        "total_so_far": papers_found,
                    },
                )

                # Update cursor after search
                search_cursors[source] = f"cursor_{source}_page_1"

            result["papers_found"] = papers_found

            # Create checkpoint after search
            progress_service.create_checkpoint(
                job_id=job_id,
                current_step=2,
                step_name="search_sources_complete",
                items_processed=[],
                items_remaining=[],
                search_cursors=search_cursors,
                accumulated_results=result,
                context_summary=f"Searched {len(sources)} sources, found {papers_found} papers total",
            )

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="search_sources",
                message=f"Search complete: found {papers_found} papers",
                data={"papers_found": papers_found, "sources": sources},
            )

        # Step 3: Collect and add papers
        if start_step <= 3:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="collect_papers",
                message="Collecting and deduplicating papers",
            )

            job.update_progress(current_step=3, message="Collecting papers...")
            db.commit()

            papers_collected = min(result["papers_found"], max_per_source * len(sources))
            result["papers_collected"] = papers_collected
            job.items_total = papers_collected

            for i in range(papers_collected):
                # Log each paper collected
                progress_service.log_paper_collected(
                    job_id=job_id,
                    message=f"Collected paper {i + 1}",
                    data={
                        "paper_index": i + 1,
                        "total": papers_collected,
                    },
                )

                # Create checkpoint every N papers
                if (i + 1) % checkpoint_interval == 0:
                    progress_service.create_checkpoint(
                        job_id=job_id,
                        current_step=3,
                        step_name="collect_papers",
                        items_processed=list(range(i + 1)),
                        items_remaining=list(range(i + 1, papers_collected)),
                        accumulated_results=result,
                        context_summary=f"Collected {i + 1}/{papers_collected} papers",
                    )

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="collect_papers",
                message=f"Collected {papers_collected} papers",
                data={"papers_collected": papers_collected},
            )
            db.commit()

        # Step 4: Process documents
        if config.get("process_documents", True) and start_step <= 4:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="process_documents",
                message="Processing documents (chunk, embed, summarize)",
            )

            job.update_progress(current_step=4, message="Processing documents...")
            db.commit()

            # Get pending documents
            pending_docs = db.execute(
                select(Document)
                .where(Document.project_id == project_id)
                .where(Document.status == DocumentStatus.PENDING)
            ).scalars().all()

            # Filter out already processed documents if resuming
            already_processed = set()
            if restored_state:
                already_processed = restored_state.get("items_processed", set())

            processed = len(already_processed)
            failed = 0
            doc_ids_processed = list(already_processed)

            for doc in pending_docs:
                if doc.id in already_processed:
                    continue

                try:
                    # Simplified processing
                    doc.status = DocumentStatus.READY
                    processed += 1
                    doc_ids_processed.append(doc.id)
                    job.items_processed = processed

                    # Log paper processed
                    progress_service.log_paper_processed(
                        job_id=job_id,
                        message=f"Processed document {doc.id}: {doc.title}",
                        data={
                            "document_id": doc.id,
                            "title": doc.title,
                            "processed_count": processed,
                        },
                    )

                    # Create checkpoint every N documents
                    if processed % checkpoint_interval == 0:
                        remaining_ids = [d.id for d in pending_docs if d.id not in doc_ids_processed]
                        result["papers_processed"] = processed
                        result["papers_failed"] = failed

                        progress_service.create_checkpoint(
                            job_id=job_id,
                            current_step=4,
                            step_name="process_documents",
                            items_processed=doc_ids_processed,
                            items_remaining=remaining_ids,
                            accumulated_results=result,
                            context_summary=f"Processed {processed} documents, {failed} failed",
                        )

                    db.commit()

                except Exception as e:
                    doc.status = DocumentStatus.ERROR
                    doc.error_message = str(e)
                    failed += 1

                    # Log error
                    progress_service.log_error(
                        job_id=job_id,
                        message=f"Failed to process document {doc.id}: {str(e)}",
                        data={
                            "document_id": doc.id,
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                        },
                    )

                    result["errors"].append({
                        "document_id": doc.id,
                        "error": str(e),
                    })
                    db.commit()

            result["papers_processed"] = processed
            result["papers_failed"] = failed

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="process_documents",
                message=f"Processed {processed} documents ({failed} failed)",
                data={"processed": processed, "failed": failed},
            )

        # Step 5: Generate synthesis
        if config.get("generate_synthesis", True) and start_step <= 5:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="generate_synthesis",
                message="Generating research synthesis",
            )

            job.update_progress(current_step=5, message="Generating synthesis...")
            db.commit()

            # Would call summarization service
            result["synthesis_generated"] = True

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="generate_synthesis",
                message="Synthesis generated successfully",
            )

        # Identify themes
        if config.get("identify_themes", True):
            progress_service.log_phase_start(
                job_id=job_id,
                phase="identify_themes",
                message="Identifying research themes",
            )

            # Would analyze collected papers
            themes = ["Theme 1", "Theme 2"]
            result["themes_identified"] = themes

            for theme in themes:
                progress_service.log_theme(
                    job_id=job_id,
                    message=f"Identified theme: {theme}",
                    data={"theme": theme},
                )

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="identify_themes",
                message=f"Identified {len(themes)} themes",
                data={"themes": themes},
            )

        # Update project status
        project.status = ProjectStatus.ACTIVE

        # Log job completion
        progress_service.log_phase_complete(
            job_id=job_id,
            phase="research_job",
            message="Research job completed successfully",
            data=result,
        )

        # Final checkpoint with complete results
        progress_service.create_checkpoint(
            job_id=job_id,
            current_step=5,
            step_name="completed",
            items_processed=[],
            items_remaining=[],
            accumulated_results=result,
            context_summary="Research job completed successfully",
        )

        # Mark job complete
        job.mark_completed(result)
        db.commit()

        return result

    except Exception as e:
        if job:
            progress_service.log_error(
                job_id=job_id,
                message=f"Research job failed: {str(e)}",
                data={
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
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
    resume_from_checkpoint: bool = False,
) -> dict:
    """
    Search sources and collect papers.

    Args:
        job_id: Job ID for tracking
        project_id: Project to add papers to
        query: Search query
        sources: Sources to search
        max_per_source: Max papers per source
        resume_from_checkpoint: Whether to resume from checkpoint

    Returns:
        Collection results
    """
    db = get_db_session()
    progress_service = JobProgressService(db)

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            db.commit()

        sources = sources or ["openalex", "crossref", "semantic_scholar", "arxiv", "pubmed"]

        # Check for checkpoint
        restored_state = None
        if resume_from_checkpoint:
            checkpoint = progress_service.get_latest_checkpoint_sync(job_id)
            if checkpoint and checkpoint.checkpoint_state:
                restored_state = _restore_from_checkpoint(checkpoint.checkpoint_state)
                progress_service.log_recovery(
                    job_id=job_id,
                    message="Resuming search and collect from checkpoint",
                    data={"checkpoint_state": checkpoint.checkpoint_state},
                )

        progress_service.log_phase_start(
            job_id=job_id,
            phase="search_and_collect",
            message=f"Starting search and collect: '{query}'",
            data={"query": query, "sources": sources},
        )

        result = {
            "query": query,
            "sources_searched": sources,
            "papers_found": {},
            "papers_added": 0,
            "papers_skipped": 0,
            "errors": [],
        }

        # Restore partial results if resuming
        if restored_state:
            result.update(restored_state.get("accumulated_results", {}))

        search_cursors = restored_state.get("search_cursors", {}) if restored_state else {}

        total_found = 0
        for source in sources:
            progress_service.log_api_call(
                job_id=job_id,
                message=f"Searching {source}",
                data={"source": source, "query": query},
            )

            # Would call source adapter here with cursor
            found = 10
            result["papers_found"][source] = found
            total_found += found

            progress_service.log_paper_found(
                job_id=job_id,
                message=f"Found {found} papers from {source}",
                data={"source": source, "count": found},
            )

            # Update cursor and create checkpoint after each source
            search_cursors[source] = f"done_{source}"
            progress_service.create_checkpoint(
                job_id=job_id,
                current_step=sources.index(source) + 1,
                step_name=f"searched_{source}",
                search_cursors=search_cursors,
                accumulated_results=result,
                context_summary=f"Searched {source}, found {found} papers",
            )

        job.items_total = total_found

        # Would add papers as documents
        result["papers_added"] = total_found
        job.items_processed = total_found

        progress_service.log_phase_complete(
            job_id=job_id,
            phase="search_and_collect",
            message=f"Search and collect complete: {total_found} papers",
            data=result,
        )

        if job:
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        if job:
            progress_service.log_error(
                job_id=job_id,
                message=f"Search and collect failed: {str(e)}",
                data={"error": str(e), "traceback": traceback.format_exc()},
            )
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
    resume_from_checkpoint: bool = False,
    checkpoint_interval: int = 10,
) -> dict:
    """
    Process all documents in a project's collection.

    Args:
        job_id: Job ID for tracking
        project_id: Project with documents
        generate_summaries: Whether to generate summaries
        extract_evidence: Whether to extract evidence
        auto_tag: Whether to auto-tag
        resume_from_checkpoint: Whether to resume from checkpoint
        checkpoint_interval: How often to create checkpoints

    Returns:
        Processing results
    """
    db = get_db_session()
    progress_service = JobProgressService(db)

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            db.commit()

        progress_service.log_phase_start(
            job_id=job_id,
            phase="process_collection",
            message=f"Processing documents for project {project_id}",
        )

        # Check for checkpoint
        already_processed = set()
        if resume_from_checkpoint:
            checkpoint = progress_service.get_latest_checkpoint_sync(job_id)
            if checkpoint and checkpoint.checkpoint_state:
                already_processed = set(checkpoint.checkpoint_state.get("items_processed", []))
                progress_service.log_recovery(
                    job_id=job_id,
                    message=f"Resuming from checkpoint, {len(already_processed)} already processed",
                    data={"already_processed_count": len(already_processed)},
                )

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
            "processed": len(already_processed),
            "failed": 0,
            "errors": [],
        }

        doc_ids_processed = list(already_processed)

        for i, doc in enumerate(documents):
            if doc.id in already_processed:
                continue

            try:
                doc.status = DocumentStatus.PROCESSING
                db.commit()

                # Would call processing services
                doc.status = DocumentStatus.READY
                result["processed"] += 1
                doc_ids_processed.append(doc.id)

                progress_service.log_paper_processed(
                    job_id=job_id,
                    message=f"Processed document: {doc.title}",
                    data={
                        "document_id": doc.id,
                        "title": doc.title,
                        "index": i + 1,
                        "total": len(documents),
                    },
                )

                job.update_progress(
                    items_processed=result["processed"],
                    message=f"Processed {result['processed']}/{len(documents)}",
                )
                db.commit()

                # Create checkpoint every N documents
                if result["processed"] % checkpoint_interval == 0:
                    remaining_ids = [d.id for d in documents if d.id not in doc_ids_processed]
                    progress_service.create_checkpoint(
                        job_id=job_id,
                        current_step=result["processed"],
                        step_name="process_collection",
                        items_processed=doc_ids_processed,
                        items_remaining=remaining_ids,
                        accumulated_results=result,
                        context_summary=f"Processed {result['processed']}/{len(documents)} documents",
                    )

            except Exception as e:
                doc.status = DocumentStatus.ERROR
                doc.error_message = str(e)
                result["failed"] += 1
                result["errors"].append({
                    "document_id": doc.id,
                    "error": str(e),
                })

                progress_service.log_error(
                    job_id=job_id,
                    message=f"Failed to process document {doc.id}",
                    data={
                        "document_id": doc.id,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    },
                )
                db.commit()

        progress_service.log_phase_complete(
            job_id=job_id,
            phase="process_collection",
            message=f"Processing complete: {result['processed']} succeeded, {result['failed']} failed",
            data=result,
        )

        if job:
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        if job:
            progress_service.log_error(
                job_id=job_id,
                message=f"Process collection failed: {str(e)}",
                data={"error": str(e), "traceback": traceback.format_exc()},
            )
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
    progress_service = JobProgressService(db)

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            db.commit()

        progress_service.log_phase_start(
            job_id=job_id,
            phase="generate_synthesis",
            message=f"Generating synthesis for project {project_id}",
        )

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
            progress_service.log_info(
                job_id=job_id,
                phase="generate_synthesis",
                message="No documents to synthesize",
            )
            if job:
                job.mark_completed(result)
                db.commit()
            return result

        job.update_progress(progress=0.3, message="Analyzing documents...")
        db.commit()

        progress_service.log_api_call(
            job_id=job_id,
            message="Calling LLM for synthesis generation",
            data={"document_count": len(documents)},
        )

        # Would call summarization service for comparative analysis
        result["synthesis"] = "Research synthesis placeholder..."

        # Log themes
        themes = [
            {"name": "Theme 1", "document_count": len(documents) // 2},
            {"name": "Theme 2", "document_count": len(documents) // 2},
        ]
        result["themes"] = themes

        for theme in themes:
            progress_service.log_theme(
                job_id=job_id,
                message=f"Identified theme: {theme['name']}",
                data=theme,
            )

        # Log insights
        key_findings = ["Key finding 1", "Key finding 2"]
        result["key_findings"] = key_findings

        for finding in key_findings:
            progress_service.log_insight(
                job_id=job_id,
                message=f"Key finding: {finding}",
                data={"finding": finding},
            )

        result["gaps"] = ["Research gap 1"]

        progress_service.log_phase_complete(
            job_id=job_id,
            phase="generate_synthesis",
            message=f"Synthesis complete: {len(themes)} themes, {len(key_findings)} findings",
            data=result,
        )

        if job:
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        if job:
            progress_service.log_error(
                job_id=job_id,
                message=f"Synthesis generation failed: {str(e)}",
                data={"error": str(e), "traceback": traceback.format_exc()},
            )
            job.mark_failed(str(e), traceback.format_exc())
            db.commit()
        raise

    finally:
        db.close()
