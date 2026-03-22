"""Celery tasks for document processing.

These tasks call the real service implementations for embedding,
summarization, and tagging.
"""

import asyncio
import traceback
from typing import Any

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal, get_sync_session
from app.models.document import Document, DocumentStatus
from app.models.job import Job

logger = get_logger(__name__)


def get_db_session() -> Session:
    """Get a synchronous database session for Celery tasks."""
    return next(get_sync_session())


async def _process_document_async(
    document_id: int,
    chunk_size: int,
    chunk_overlap: int,
    generate_summary: bool,
    extract_evidence: bool,
    auto_tag: bool,
    progress_callback: Any = None,
) -> dict:
    """
    Async implementation of document processing.

    Args:
        document_id: Document to process
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        generate_summary: Whether to generate summary
        extract_evidence: Whether to extract evidence
        auto_tag: Whether to auto-tag
        progress_callback: Optional callback for progress updates

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

        result = {
            "document_id": document_id,
            "title": document.title,
            "chunks_created": 0,
            "embeddings_generated": 0,
            "summary_generated": False,
            "evidence_extracted": False,
            "tags_generated": False,
            "tokens_used": 0,
        }

        # Step 1: Chunking
        chunking_service = ChunkingService(
            strategy=ChunkingStrategy.SENTENCE,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )

        chunks = chunking_service.chunk_document(
            abstract=document.abstract,
            full_text=document.full_text,
        )

        # Store chunks in database
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

        # Step 2: Generate embeddings
        if chunks:
            embedding_service = EmbeddingService(db)

            # Get the chunks we just created
            db_chunks = await doc_service.get_chunks(document_id)

            embedding_result = await embedding_service.embed_chunks(db_chunks)

            # Store embeddings
            for emb_result in embedding_result.successful:
                await doc_service.update_chunk_embedding(
                    chunk_id=emb_result.chunk_id,
                    embedding=emb_result.embedding,
                    model=emb_result.model,
                )

            result["embeddings_generated"] = len(embedding_result.successful)
            result["embedding_model"] = (
                embedding_result.successful[0].model
                if embedding_result.successful
                else None
            )
            result["tokens_used"] += embedding_result.total_tokens

            # Update document embedding model
            if embedding_result.successful:
                document.embedding_model = embedding_result.successful[0].model

            await db.commit()

        # Step 3: Summarization
        if generate_summary and (document.abstract or document.full_text):
            summarization_service = SummarizationService(db)

            try:
                summary_result = await summarization_service.summarize(
                    document, SummaryLevel.STANDARD
                )
                await doc_service.set_summary(document_id, summary_result.summary)
                result["summary_generated"] = True
                result["summary"] = summary_result.summary
                result["tokens_used"] += summary_result.tokens_used
                await db.commit()
            except Exception as e:
                result["summary_error"] = str(e)

        # Step 4: Evidence extraction
        if extract_evidence and (document.abstract or document.full_text):
            summarization_service = SummarizationService(db)

            try:
                # Extract key findings
                findings = await summarization_service.extract_key_findings(document)
                await doc_service.set_key_findings(document_id, findings)
                result["key_findings_count"] = len(findings)

                # Extract evidence claims
                claims = await summarization_service.extract_evidence_claims(document)
                await doc_service.set_evidence_claims(document_id, claims)
                result["evidence_claims_count"] = len(claims)

                result["evidence_extracted"] = True
                await db.commit()
            except Exception as e:
                result["evidence_error"] = str(e)

        # Step 5: Auto-tagging
        if auto_tag:
            tagging_service = TaggingService(db)

            try:
                tags = await tagging_service.auto_tag_document(
                    document_id, use_ai=True, min_confidence=0.5
                )
                result["tags_generated"] = True
                result["tags"] = tags
                result["tags_count"] = len(tags)
            except Exception as e:
                result["tags_error"] = str(e)

        # Update document status
        document.status = DocumentStatus.READY
        document.chunk_count = len(chunks)
        await db.commit()

        return result


@shared_task(bind=True, name="app.worker.tasks.documents.process_document")
def process_document_task(
    self: Any,
    job_id: int,
    document_id: int,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    generate_summary: bool = True,
    extract_evidence: bool = True,
    auto_tag: bool = True,
) -> dict:
    """
    Process a single document: chunk, embed, summarize, tag.

    Args:
        job_id: Job ID for tracking
        document_id: Document to process
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
        generate_summary: Whether to generate summary
        extract_evidence: Whether to extract evidence
        auto_tag: Whether to auto-tag

    Returns:
        Processing result dict
    """
    db = get_db_session()

    try:
        # Get job and update status
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            job.progress_message = "Starting document processing..."
            db.commit()

        # Get document and update status
        document = db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        document.status = DocumentStatus.PROCESSING
        db.commit()

        # Update progress
        if job:
            job.update_progress(progress=0.1, message="Processing document...")
            db.commit()

        # Run async processing
        result = asyncio.run(
            _process_document_async(
                document_id=document_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                generate_summary=generate_summary,
                extract_evidence=extract_evidence,
                auto_tag=auto_tag,
            )
        )

        # Mark job complete
        if job:
            job.items_processed = 1
            job.items_total = 1
            job.mark_completed(result)
            db.commit()

        return result

    except Exception as e:
        # Handle failure
        if job:
            job.mark_failed(str(e), traceback.format_exc())
            db.commit()

        # Update document status
        try:
            document = db.execute(
                select(Document).where(Document.id == document_id)
            ).scalar_one_or_none()
            if document:
                document.status = DocumentStatus.ERROR
                document.error_message = str(e)
                db.commit()
        except Exception as e:
            logger.debug(f"Failed to update document status after error: {e}")

        raise

    finally:
        db.close()


async def _embed_document_async(document_id: int) -> dict:
    """Async implementation of document embedding."""
    from app.services.document import DocumentService
    from app.services.embedding import EmbeddingService

    async with AsyncSessionLocal() as db:
        doc_service = DocumentService(db)
        document = await doc_service.get(document_id)

        # Get existing chunks
        chunks = await doc_service.get_chunks(document_id)

        if not chunks:
            return {
                "document_id": document_id,
                "chunks_embedded": 0,
                "model": None,
                "error": "No chunks found - document may need chunking first",
            }

        # Generate embeddings
        embedding_service = EmbeddingService(db)
        embedding_result = await embedding_service.embed_chunks(chunks)

        # Store embeddings
        for emb_result in embedding_result.successful:
            await doc_service.update_chunk_embedding(
                chunk_id=emb_result.chunk_id,
                embedding=emb_result.embedding,
                model=emb_result.model,
            )

        # Update document embedding model
        if embedding_result.successful:
            document.embedding_model = embedding_result.successful[0].model

        await db.commit()

        return {
            "document_id": document_id,
            "chunks_embedded": len(embedding_result.successful),
            "chunks_failed": len(embedding_result.failed),
            "model": (
                embedding_result.successful[0].model
                if embedding_result.successful
                else None
            ),
            "tokens_used": embedding_result.total_tokens,
        }


@shared_task(bind=True, name="app.worker.tasks.documents.embed_document")
def embed_document_task(
    self: Any,
    job_id: int,
    document_id: int,
) -> dict:
    """
    Generate embeddings for a document's chunks.

    Args:
        job_id: Job ID for tracking
        document_id: Document to embed

    Returns:
        Embedding result dict
    """
    db = get_db_session()

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            job.progress_message = "Generating embeddings..."
            db.commit()

        # Run async embedding
        result = asyncio.run(_embed_document_async(document_id))

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


async def _summarize_document_async(document_id: int, level: str) -> dict:
    """Async implementation of document summarization."""
    from app.services.document import DocumentService
    from app.services.summarization import SummarizationService, SummaryLevel

    async with AsyncSessionLocal() as db:
        doc_service = DocumentService(db)
        document = await doc_service.get(document_id)

        if not document.abstract and not document.full_text:
            return {
                "document_id": document_id,
                "level": level,
                "summary": None,
                "error": "Document has no content to summarize",
            }

        # Map level string to enum
        level_enum = (
            SummaryLevel(level)
            if level in [e.value for e in SummaryLevel]
            else SummaryLevel.STANDARD
        )

        summarization_service = SummarizationService(db)
        summary_result = await summarization_service.summarize(document, level_enum)

        # Save summary to document
        await doc_service.set_summary(document_id, summary_result.summary)
        await db.commit()

        return {
            "document_id": document_id,
            "level": level,
            "summary": summary_result.summary,
            "model": summary_result.model,
            "tokens_used": summary_result.tokens_used,
        }


@shared_task(bind=True, name="app.worker.tasks.documents.summarize_document")
def summarize_document_task(
    self: Any,
    job_id: int,
    document_id: int,
    level: str = "standard",
) -> dict:
    """
    Generate summary for a document.

    Args:
        job_id: Job ID for tracking
        document_id: Document to summarize
        level: Summary level (brief, standard, detailed)

    Returns:
        Summarization result dict
    """
    db = get_db_session()

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            job.progress_message = "Generating summary..."
            db.commit()

        # Run async summarization
        result = asyncio.run(_summarize_document_async(document_id, level))

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


async def _batch_process_async(
    project_id: int,
    document_ids: list[int] | None,
    operations: list[str],
    progress_callback: Any = None,
) -> dict:
    """Async implementation of batch document processing."""
    from app.services.chunking import ChunkingService, ChunkingStrategy
    from app.services.document import DocumentService
    from app.services.embedding import EmbeddingService
    from app.services.summarization import SummarizationService, SummaryLevel
    from app.services.tagging import TaggingService

    async with AsyncSessionLocal() as db:
        doc_service = DocumentService(db)

        # Get documents to process
        if document_ids:
            documents = []
            for doc_id in document_ids:
                try:
                    doc = await doc_service.get(doc_id)
                    documents.append(doc)
                except Exception as e:
                    logger.debug(f"Failed to fetch document {doc_id}: {e}")
        else:
            documents, _ = await doc_service.list(
                project_id, page_size=1000, status=DocumentStatus.PENDING
            )

        result = {
            "project_id": project_id,
            "total_documents": len(documents),
            "processed": 0,
            "failed": 0,
            "operations": operations,
            "errors": [],
        }

        for doc in documents:
            try:
                doc.status = DocumentStatus.PROCESSING
                await db.commit()

                # Chunking (if needed and requested)
                if "chunk" in operations or "embed" in operations:
                    existing_chunks = await doc_service.get_chunks(doc.id)
                    if not existing_chunks:
                        chunking_service = ChunkingService(
                            strategy=ChunkingStrategy.SENTENCE,
                            chunk_size=1000,
                            overlap=200,
                        )
                        chunks = chunking_service.chunk_document(
                            abstract=doc.abstract,
                            full_text=doc.full_text,
                        )
                        for chunk in chunks:
                            await doc_service.add_chunk(
                                document_id=doc.id,
                                content=chunk.content,
                                chunk_index=chunk.index,
                                start_char=chunk.start_char,
                                end_char=chunk.end_char,
                                section_type=chunk.section_type,
                                section_title=chunk.section_title,
                                token_count=chunk.token_count,
                            )
                        await db.commit()

                # Embedding
                if "embed" in operations:
                    chunks = await doc_service.get_chunks(doc.id)
                    if chunks:
                        embedding_service = EmbeddingService(db)
                        embedding_result = await embedding_service.embed_chunks(chunks)
                        for emb_result in embedding_result.successful:
                            await doc_service.update_chunk_embedding(
                                chunk_id=emb_result.chunk_id,
                                embedding=emb_result.embedding,
                                model=emb_result.model,
                            )
                        if embedding_result.successful:
                            doc.embedding_model = embedding_result.successful[0].model
                        await db.commit()

                # Summarization
                if "summarize" in operations and (doc.abstract or doc.full_text):
                    summarization_service = SummarizationService(db)
                    try:
                        summary_result = await summarization_service.summarize(
                            doc, SummaryLevel.STANDARD
                        )
                        await doc_service.set_summary(doc.id, summary_result.summary)
                        await db.commit()
                    except Exception as e:
                        logger.warning(
                            f"Summary generation failed for document {doc.id}: {e}"
                        )

                # Tagging
                if "tag" in operations:
                    tagging_service = TaggingService(db)
                    try:
                        await tagging_service.auto_tag_document(doc.id, use_ai=True)
                    except Exception as e:
                        logger.warning(
                            f"Auto-tagging failed for document {doc.id}: {e}"
                        )

                # Mark as ready
                doc.status = DocumentStatus.READY
                await db.commit()
                result["processed"] += 1

            except Exception as e:
                doc.status = DocumentStatus.ERROR
                doc.error_message = str(e)
                await db.commit()
                result["failed"] += 1
                result["errors"].append(
                    {
                        "document_id": doc.id,
                        "error": str(e),
                    }
                )

        return result


@shared_task(bind=True, name="app.worker.tasks.documents.batch_process")
def batch_process_task(
    self: Any,
    job_id: int,
    project_id: int,
    document_ids: list[int] | None = None,
    operations: list[str] | None = None,
) -> dict:
    """
    Batch process multiple documents.

    Args:
        job_id: Job ID for tracking
        project_id: Project containing documents
        document_ids: Specific documents (None = all pending)
        operations: Operations to perform (chunk, embed, summarize, tag)

    Returns:
        Batch processing result
    """
    db = get_db_session()

    try:
        job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
        if job:
            job.celery_task_id = self.request.id
            job.mark_started()
            job.progress_message = "Starting batch processing..."
            db.commit()

        operations = operations or ["chunk", "embed", "summarize", "tag"]

        # Run async batch processing
        result = asyncio.run(
            _batch_process_async(
                project_id=project_id,
                document_ids=document_ids,
                operations=operations,
            )
        )

        if job:
            job.items_total = result["total_documents"]
            job.items_processed = result["processed"]
            job.items_failed = result["failed"]
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
