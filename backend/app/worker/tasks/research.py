"""Celery tasks for research workflow with progress logging and checkpointing."""

import asyncio
import traceback
from typing import Any

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal, get_sync_session
from app.models.document import Document, DocumentStatus
from app.models.job import Job, JobStatus
from app.models.project import Project, ProjectStatus
from app.schemas.paper import SearchFilters
from app.services.job_progress import JobProgressService
from app.sources.manager import get_source_manager

logger = get_logger(__name__)


async def _generate_synthesis_async(documents: list, research_objective: str) -> str:
    """
    Generate a synthesis of research findings using the summarization service.

    Args:
        documents: List of Document objects to synthesize
        research_objective: The research objective for context

    Returns:
        Synthesis text
    """
    from app.services.summarization import SummarizationService

    async with AsyncSessionLocal() as db:
        summarization_service = SummarizationService(db)

        # Use comparative summary for synthesis
        synthesis = await summarization_service.generate_comparative_summary(documents)

        return synthesis


async def _process_single_document_async(
    document_id: int,
    generate_summaries: bool = True,
    extract_evidence: bool = True,
    auto_tag: bool = True,
) -> dict:
    """
    Process a single document with chunking, embedding, summarization, and tagging.

    Args:
        document_id: Document to process
        generate_summaries: Whether to generate summaries
        extract_evidence: Whether to extract evidence
        auto_tag: Whether to auto-tag

    Returns:
        Processing result dict
    """
    from app.services.chunking import ChunkingService, ChunkingStrategy
    from app.services.document import DocumentService
    from app.services.embedding import EmbeddingService
    from app.services.summarization import SummarizationService, SummaryLevel
    from app.services.tagging import TaggingService

    async with AsyncSessionLocal() as db:
        doc_service = DocumentService(db)
        document = await doc_service.get(document_id)

        result = {"document_id": document_id}

        # Check if document has content
        if not document.abstract and not document.full_text:
            result["skipped"] = True
            result["reason"] = "No content to process"
            return result

        # Chunking
        chunking_service = ChunkingService(
            strategy=ChunkingStrategy.SENTENCE,
            chunk_size=1000,
            overlap=200,
        )
        chunks = chunking_service.chunk_document(
            abstract=document.abstract,
            full_text=document.full_text,
        )

        # Store chunks
        for chunk in chunks:
            await doc_service.add_chunk(
                document_id=document_id,
                content=chunk.content,
                chunk_index=chunk.index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                section_type=chunk.section_type,
                section_title=chunk.section_title,
                token_count=chunk.token_count,
            )
        await db.commit()
        result["chunks_created"] = len(chunks)

        # Embedding
        if chunks:
            embedding_service = EmbeddingService(db)
            db_chunks = await doc_service.get_chunks(document_id)
            embedding_result = await embedding_service.embed_chunks(db_chunks)

            for emb in embedding_result.successful:
                await doc_service.update_chunk_embedding(
                    chunk_id=emb.chunk_id,
                    embedding=emb.embedding,
                    model=emb.model,
                )

            if embedding_result.successful:
                document.embedding_model = embedding_result.successful[0].model
            await db.commit()
            result["embeddings_generated"] = len(embedding_result.successful)

        # Summarization
        if generate_summaries:
            try:
                summarization_service = SummarizationService(db)
                summary_result = await summarization_service.summarize(
                    document, SummaryLevel.STANDARD
                )
                await doc_service.set_summary(document_id, summary_result.summary)
                await db.commit()
                result["summary_generated"] = True
            except Exception as e:
                result["summary_generated"] = False
                result["summary_error"] = str(e)
                logger.warning(f"Summarization failed for doc {document_id}: {e}", exc_info=True)

        # Evidence extraction
        if extract_evidence:
            try:
                summarization_service = SummarizationService(db)
                findings = await summarization_service.extract_key_findings(document)
                await doc_service.set_key_findings(document_id, findings)
                claims = await summarization_service.extract_evidence_claims(document)
                await doc_service.set_evidence_claims(document_id, claims)
                await db.commit()
                result["evidence_extracted"] = True
            except Exception as e:
                result["evidence_extracted"] = False
                result["evidence_error"] = str(e)
                logger.warning(f"Evidence extraction failed for doc {document_id}: {e}", exc_info=True)

        # Tagging
        if auto_tag:
            try:
                tagging_service = TaggingService(db)
                await tagging_service.auto_tag_document(document_id, use_ai=True)
                result["tags_generated"] = True
            except Exception as e:
                result["tags_generated"] = False
                result["tagging_error"] = str(e)
                logger.warning(f"Tagging failed for doc {document_id}: {e}", exc_info=True)

        # Update document
        document.status = DocumentStatus.READY
        document.chunk_count = len(chunks)
        await db.commit()

        return result


async def _identify_themes_async(documents: list) -> list[dict]:
    """
    Identify research themes from a collection of documents.

    Args:
        documents: List of Document objects to analyze

    Returns:
        List of theme dictionaries with name, description, and document_count
    """
    import json

    from app.providers import get_provider_manager

    # Build context from documents
    doc_summaries = []
    for doc in documents[:15]:  # Limit for context
        summary = doc.summary or doc.abstract or ""
        if summary:
            doc_summaries.append(f"- {doc.title}: {summary[:300]}...")

    if not doc_summaries:
        return []

    all_summaries = "\n".join(doc_summaries)

    prompt = f"""Analyze the following {len(documents)} academic papers and identify 3-5 major research themes.

Papers:
{all_summaries}

Return a JSON array of themes:
[
  {{
    "name": "Theme name",
    "description": "Brief description of the theme",
    "document_count": approximate_number_of_papers_in_this_theme
  }}
]

Focus on conceptual themes that group multiple papers. Return only valid JSON."""

    manager = get_provider_manager()
    provider = manager.get_default()

    if not provider:
        return []

    try:
        response = await provider.complete(prompt=prompt)
        content = response.content.strip()

        # Parse JSON response
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        themes = json.loads(content)
        if not isinstance(themes, list):
            themes = [themes]

        return themes
    except Exception:
        return []


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
    self: Any,
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
                        "items_already_processed": len(
                            restored_state["items_processed"]
                        ),
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
            message=f"Starting research job for project '{project.name}'",
            data={
                "project_id": project_id,
                "config": config,
                "resume_from_checkpoint": resume_from_checkpoint,
                "start_step": start_step,
            },
        )

        # Initialize variables that are used across steps
        found_papers = []

        # Always build search query (needed for Step 2)
        scope = project.scope or {}
        keywords = scope.get("keywords", [])
        if not keywords and project.research_objective:
            # Extract keywords from objective
            keywords = project.research_objective.split()[:5]
        search_query = " ".join(keywords[:10]) if keywords else project.research_objective[:100]

        # Step 1: Build search query from project scope
        if start_step <= 1:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="build_query",
                message="Building search query from project scope",
            )

            job.update_progress(current_step=1, message="Building search query...")
            db.commit()

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

            max_per_source = config.get("max_papers_per_source", project.max_results_per_source or 100)
            sources = config.get("sources") or project.sources_enabled or [
                "openalex",
                "crossref",
                "semantic_scholar",
            ]

            # Build search filters from project scope
            scope = project.scope or {}
            search_filters = SearchFilters(
                keywords=scope.get("keywords", []),
                year_from=int(scope.get("date_range_start", "1900")[:4]) if scope.get("date_range_start") else None,
                year_to=int(scope.get("date_range_end", "2100")[:4]) if scope.get("date_range_end") else None,
                open_access_only=scope.get("open_access_only", False),
                min_citations=scope.get("min_citations", 0),
            )

            # Get search cursors if resuming
            search_cursors = {}
            if restored_state:
                search_cursors = restored_state.get("search_cursors", {})

            # Log API call
            progress_service.log_api_call(
                job_id=job_id,
                message=f"Searching {len(sources)} sources: {', '.join(sources)}",
                data={
                    "sources": sources,
                    "query": search_query,
                    "filters": search_filters.model_dump(),
                },
            )

            # Call the real source manager to search
            source_manager = get_source_manager()
            search_result = asyncio.run(
                source_manager.search(
                    query=search_query,
                    filters=search_filters,
                    sources=sources,
                    page=1,
                    page_size=max_per_source,
                    deduplicate=True,
                )
            )

            # Store papers for Step 3
            found_papers = search_result.papers
            papers_found = len(found_papers)

            # Log papers found from each source
            for source_name, count in search_result.total_from_sources.items():
                progress_service.log_paper_found(
                    job_id=job_id,
                    message=f"Found {count} papers from {source_name}",
                    data={
                        "source": source_name,
                        "count": count,
                    },
                )

            # Log any errors
            for source_name, error_msg in search_result.errors.items():
                progress_service.log_error(
                    job_id=job_id,
                    message=f"Error searching {source_name}: {error_msg}",
                    data={"source": source_name, "error": error_msg},
                )
                result["errors"].append({"source": source_name, "error": error_msg})

            result["papers_found"] = papers_found
            result["papers_from_sources"] = search_result.total_from_sources
            result["deduplicated_count"] = search_result.deduplicated_count
            result["original_count"] = search_result.original_count

            # Create checkpoint after search
            progress_service.create_checkpoint(
                job_id=job_id,
                current_step=2,
                step_name="search_sources_complete",
                items_processed=[],
                items_remaining=[],
                search_cursors=search_cursors,
                accumulated_results=result,
                context_summary=f"Searched {len(sources)} sources, found {papers_found} papers (deduplicated)",
            )

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="search_sources",
                message=f"Search complete: found {papers_found} papers (from {search_result.original_count} before dedup)",
                data={"papers_found": papers_found, "sources": sources},
            )

        # Step 3: Collect and add papers as documents
        if start_step <= 3:
            progress_service.log_phase_start(
                job_id=job_id,
                phase="collect_papers",
                message="Adding papers to project as documents",
            )

            job.update_progress(current_step=3, message="Adding papers to project...")
            db.commit()

            # Get papers from search result (stored in Step 2)
            papers_to_add = found_papers
            papers_collected = 0
            papers_skipped = 0
            job.items_total = len(papers_to_add)
            db.commit()

            for i, paper in enumerate(papers_to_add):
                try:
                    # Check if paper already exists (by DOI)
                    if paper.doi:
                        existing = db.execute(
                            select(Document).where(
                                Document.project_id == project_id,
                                Document.doi == paper.doi
                            )
                        ).scalar_one_or_none()
                        if existing:
                            papers_skipped += 1
                            continue

                    # Create document from paper
                    document = Document(
                        project_id=project_id,
                        title=paper.title,
                        abstract=paper.abstract,
                        authors=[a.model_dump() for a in paper.authors],
                        document_type=paper.document_type.value if paper.document_type else "journal-article",
                        publication_date=paper.publication_date.isoformat() if paper.publication_date else None,
                        year=paper.year,
                        journal=paper.journal.model_dump() if paper.journal else None,
                        language=paper.language,
                        doi=paper.doi,
                        identifiers=[i.model_dump() for i in paper.identifiers],
                        url=str(paper.url) if paper.url else None,
                        pdf_url=str(paper.pdf_url) if paper.pdf_url else None,
                        open_access_url=str(paper.open_access_url) if paper.open_access_url else None,
                        citation_count=paper.citation_count,
                        reference_count=paper.reference_count,
                        keywords=paper.keywords,
                        subjects=paper.subjects,
                        mesh_terms=paper.mesh_terms,
                        tags=[],
                        is_open_access=paper.is_open_access,
                        is_preprint=paper.is_preprint,
                        is_retracted=paper.is_retracted,
                        source_name=paper.primary_source,
                        source_id=paper.sources[0].id if paper.sources else None,
                        source_url=str(paper.sources[0].url) if paper.sources and paper.sources[0].url else None,
                        status=DocumentStatus.PENDING,
                    )
                    db.add(document)
                    papers_collected += 1

                    # Log each paper collected
                    progress_service.log_paper_collected(
                        job_id=job_id,
                        message=f"Added: {paper.title[:50]}..." if len(paper.title) > 50 else f"Added: {paper.title}",
                        data={
                            "paper_index": i + 1,
                            "total": len(papers_to_add),
                            "title": paper.title,
                            "doi": paper.doi,
                        },
                    )

                    job.items_processed = papers_collected
                    db.commit()

                    # Create checkpoint every N papers
                    if papers_collected % checkpoint_interval == 0:
                        progress_service.create_checkpoint(
                            job_id=job_id,
                            current_step=3,
                            step_name="collect_papers",
                            items_processed=list(range(papers_collected)),
                            items_remaining=list(range(papers_collected, len(papers_to_add))),
                            accumulated_results=result,
                            context_summary=f"Collected {papers_collected}/{len(papers_to_add)} papers",
                        )

                except Exception as e:
                    progress_service.log_error(
                        job_id=job_id,
                        message=f"Failed to add paper: {str(e)}",
                        data={"paper_title": paper.title, "error": str(e)},
                    )
                    result["errors"].append({"paper": paper.title, "error": str(e)})

            result["papers_collected"] = papers_collected
            result["papers_skipped"] = papers_skipped

            progress_service.log_phase_complete(
                job_id=job_id,
                phase="collect_papers",
                message=f"Added {papers_collected} papers to project ({papers_skipped} duplicates skipped)",
                data={"papers_collected": papers_collected, "papers_skipped": papers_skipped},
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
            pending_docs = (
                db.execute(
                    select(Document)
                    .where(Document.project_id == project_id)
                    .where(Document.status == DocumentStatus.PENDING)
                )
                .scalars()
                .all()
            )

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
                    # Call real document processing (chunking, embedding, summarization)
                    doc.status = DocumentStatus.PROCESSING
                    db.commit()

                    asyncio.run(
                        _process_single_document_async(
                            doc.id,
                            generate_summaries=config.get("generate_summaries", True),
                            extract_evidence=config.get("extract_evidence", True),
                            auto_tag=config.get("auto_tag", True),
                        )
                    )

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
                        remaining_ids = [
                            d.id for d in pending_docs if d.id not in doc_ids_processed
                        ]
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

                    result["errors"].append(
                        {
                            "document_id": doc.id,
                            "error": str(e),
                        }
                    )
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

            # Get ready documents for synthesis
            ready_docs = (
                db.execute(
                    select(Document)
                    .where(Document.project_id == project_id)
                    .where(Document.status == DocumentStatus.READY)
                    .limit(10)  # Limit for context window
                )
                .scalars()
                .all()
            )

            if ready_docs:
                try:
                    # Generate comparative synthesis using real summarization service
                    synthesis = asyncio.run(
                        _generate_synthesis_async(ready_docs, project.research_objective)
                    )
                    result["synthesis"] = synthesis
                    result["synthesis_generated"] = True
                    result["documents_synthesized"] = len(ready_docs)

                    progress_service.log_phase_complete(
                        job_id=job_id,
                        phase="generate_synthesis",
                        message=f"Synthesis generated from {len(ready_docs)} documents",
                        data={"documents_count": len(ready_docs)},
                    )
                except Exception as e:
                    result["synthesis_error"] = str(e)
                    result["synthesis_generated"] = False
                    progress_service.log_error(
                        job_id=job_id,
                        message=f"Synthesis generation failed: {str(e)}",
                        data={"error": str(e)},
                    )
            else:
                result["synthesis_generated"] = False
                result["synthesis_error"] = "No documents available for synthesis"

        # Identify themes
        if config.get("identify_themes", True):
            progress_service.log_phase_start(
                job_id=job_id,
                phase="identify_themes",
                message="Identifying research themes",
            )

            # Get documents for theme analysis
            docs_for_themes = (
                db.execute(
                    select(Document)
                    .where(Document.project_id == project_id)
                    .where(Document.status == DocumentStatus.READY)
                    .limit(20)
                )
                .scalars()
                .all()
            )

            if docs_for_themes:
                try:
                    # Extract themes using real analysis
                    themes = asyncio.run(_identify_themes_async(docs_for_themes))
                    result["themes_identified"] = themes

                    for theme in themes:
                        progress_service.log_theme(
                            job_id=job_id,
                            message=f"Identified theme: {theme.get('name', theme)}",
                            data={"theme": theme},
                        )

                    progress_service.log_phase_complete(
                        job_id=job_id,
                        phase="identify_themes",
                        message=f"Identified {len(themes)} themes",
                        data={"themes": themes},
                    )
                except Exception as e:
                    result["themes_identified"] = []
                    result["themes_error"] = str(e)
                    progress_service.log_error(
                        job_id=job_id,
                        message=f"Theme identification failed: {str(e)}",
                        data={"error": str(e)},
                    )
            else:
                result["themes_identified"] = []

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
    self: Any,
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

        sources = sources or [
            "openalex",
            "crossref",
            "semantic_scholar",
            "arxiv",
            "pubmed",
        ]

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

        search_cursors = (
            restored_state.get("search_cursors", {}) if restored_state else {}
        )

        # Call the real source manager to search
        progress_service.log_api_call(
            job_id=job_id,
            message=f"Searching {len(sources)} sources",
            data={"sources": sources, "query": query},
        )

        source_manager = get_source_manager()
        search_result = asyncio.run(
            source_manager.search(
                query=query,
                filters=None,
                sources=sources,
                page=1,
                page_size=max_per_source,
                deduplicate=True,
            )
        )

        # Log results from each source
        for source_name, count in search_result.total_from_sources.items():
            result["papers_found"][source_name] = count
            progress_service.log_paper_found(
                job_id=job_id,
                message=f"Found {count} papers from {source_name}",
                data={"source": source_name, "count": count},
            )
            search_cursors[source_name] = "done"

        # Log any errors
        for source_name, error_msg in search_result.errors.items():
            result["errors"].append({"source": source_name, "error": error_msg})

        total_found = len(search_result.papers)
        job.items_total = total_found
        db.commit()

        # Add papers as documents
        papers_added = 0
        papers_skipped = 0

        for paper in search_result.papers:
            try:
                # Check if paper already exists (by DOI)
                if paper.doi:
                    existing = db.execute(
                        select(Document).where(
                            Document.project_id == project_id,
                            Document.doi == paper.doi
                        )
                    ).scalar_one_or_none()
                    if existing:
                        papers_skipped += 1
                        continue

                # Create document from paper
                document = Document(
                    project_id=project_id,
                    title=paper.title,
                    abstract=paper.abstract,
                    authors=[a.model_dump() for a in paper.authors],
                    document_type=paper.document_type.value if paper.document_type else "journal-article",
                    year=paper.year,
                    doi=paper.doi,
                    url=str(paper.url) if paper.url else None,
                    pdf_url=str(paper.pdf_url) if paper.pdf_url else None,
                    citation_count=paper.citation_count,
                    is_open_access=paper.is_open_access,
                    source_name=paper.primary_source,
                    status=DocumentStatus.PENDING,
                )
                db.add(document)
                papers_added += 1
                db.commit()

            except Exception as e:
                result["errors"].append({"paper": paper.title, "error": str(e)})

        result["papers_added"] = papers_added
        result["papers_skipped"] = papers_skipped
        job.items_processed = papers_added

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
    self: Any,
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
                already_processed = set(
                    checkpoint.checkpoint_state.get("items_processed", [])
                )
                progress_service.log_recovery(
                    job_id=job_id,
                    message=f"Resuming from checkpoint, {len(already_processed)} already processed",
                    data={"already_processed_count": len(already_processed)},
                )

        # Get pending documents
        documents = (
            db.execute(
                select(Document)
                .where(Document.project_id == project_id)
                .where(
                    Document.status.in_([DocumentStatus.PENDING, DocumentStatus.ERROR])
                )
            )
            .scalars()
            .all()
        )

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

                # Call real document processing
                try:
                    asyncio.run(
                        _process_single_document_async(
                            doc.id,
                            generate_summaries=generate_summaries,
                            extract_evidence=extract_evidence,
                            auto_tag=auto_tag,
                        )
                    )
                    doc.status = DocumentStatus.READY
                except Exception as proc_error:
                    doc.status = DocumentStatus.ERROR
                    doc.error_message = str(proc_error)
                    raise proc_error

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
                    remaining_ids = [
                        d.id for d in documents if d.id not in doc_ids_processed
                    ]
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
                result["errors"].append(
                    {
                        "document_id": doc.id,
                        "error": str(e),
                    }
                )

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
    self: Any,
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
        documents = (
            db.execute(
                select(Document)
                .where(Document.project_id == project_id)
                .where(Document.status == DocumentStatus.READY)
            )
            .scalars()
            .all()
        )

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

        # Get project for research objective
        project = db.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        research_objective = project.research_objective if project else ""

        # Generate synthesis using real summarization service
        try:
            synthesis = asyncio.run(
                _generate_synthesis_async(documents, research_objective)
            )
            result["synthesis"] = synthesis
        except Exception as e:
            result["synthesis"] = f"Synthesis generation failed: {str(e)}"
            result["synthesis_error"] = str(e)

        # Identify themes using real AI analysis
        try:
            themes = asyncio.run(_identify_themes_async(documents))
            result["themes"] = themes

            for theme in themes:
                progress_service.log_theme(
                    job_id=job_id,
                    message=f"Identified theme: {theme.get('name', 'Unknown')}",
                    data=theme,
                )
        except Exception as e:
            result["themes"] = []
            result["themes_error"] = str(e)

        # Extract key findings from document summaries
        key_findings = []
        for doc in documents[:10]:  # Limit to first 10
            if doc.key_findings:
                for finding in doc.key_findings[:2]:
                    if isinstance(finding, dict):
                        key_findings.append(finding.get("finding", str(finding)))
                    else:
                        key_findings.append(str(finding))
        result["key_findings"] = key_findings[:10]  # Limit total findings

        for finding in result["key_findings"]:
            progress_service.log_insight(
                job_id=job_id,
                message=f"Key finding: {finding}",
                data={"finding": finding},
            )

        # Identify research gaps from themes and findings
        result["gaps"] = []  # Would require additional analysis

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
