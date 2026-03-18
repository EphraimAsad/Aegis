"""Document management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import DocumentStatus
from app.schemas.advanced_search import (
    AdvancedSearchRequest,
    AdvancedSearchResponse,
)
from app.schemas.document import (
    AddPaperRequest,
    BulkAddPapersRequest,
    BulkAddPapersResponse,
    DocumentChunkResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentSummary,
    DocumentUpdate,
    ProcessingRequest,
    ProcessingStatus,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SimilarChunkResult,
)
from app.services.advanced_search import AdvancedSearchService
from app.services.chunking import ChunkingStrategy
from app.services.document import DocumentService
from app.services.embedding import get_embedding_service
from app.services.retrieval import get_retrieval_service
from app.services.summarization import SummaryLevel, get_summarization_service
from app.services.tagging import get_tagging_service
from app.sources import get_source_manager

router = APIRouter()


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    request: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Create a new document manually.

    For adding papers from search results, use the /add-paper endpoint instead.
    """
    service = DocumentService(db)
    document = await service.create(request)
    await db.commit()
    return DocumentResponse.model_validate(document)


@router.post("/add-paper", response_model=DocumentResponse, status_code=201)
async def add_paper_from_search(
    project_id: int,
    request: AddPaperRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Add a paper from search results to the document library.

    Fetches the paper metadata from the source and adds it to the project.
    """
    service = DocumentService(db)
    source_manager = get_source_manager()

    # Fetch paper from source
    paper = None
    if request.doi:
        paper = await source_manager.get_by_doi(
            request.doi,
            [request.source_name] if request.source_name else None,
        )
    elif request.source_name and request.source_id:
        source = source_manager.get(request.source_name)
        if source:
            paper = await source.get_by_id(request.source_id)

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Paper not found in specified source",
        )

    try:
        document = await service.create_from_paper(
            project_id=project_id,
            paper=paper,
            tags=request.tags,
        )
        await db.commit()
        return DocumentResponse.model_validate(document)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/bulk-add", response_model=BulkAddPapersResponse)
async def bulk_add_papers(
    project_id: int,
    request: BulkAddPapersRequest,
    db: AsyncSession = Depends(get_db),
) -> BulkAddPapersResponse:
    """
    Add multiple papers to the document library.
    """
    service = DocumentService(db)
    source_manager = get_source_manager()

    added = 0
    skipped = 0
    errors = []

    for paper_req in request.papers:
        try:
            paper = None
            if paper_req.doi:
                paper = await source_manager.get_by_doi(
                    paper_req.doi,
                    [paper_req.source_name] if paper_req.source_name else None,
                )

            if not paper:
                errors.append({"doi": paper_req.doi, "error": "Paper not found"})
                continue

            await service.create_from_paper(
                project_id=project_id,
                paper=paper,
                tags=paper_req.tags,
            )
            added += 1

        except Exception as e:
            if "already exists" in str(e):
                skipped += 1
            else:
                errors.append({"doi": paper_req.doi, "error": str(e)})

    await db.commit()

    return BulkAddPapersResponse(added=added, skipped=skipped, errors=errors)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: DocumentStatus | None = None,
    tags: str | None = Query(None, description="Comma-separated tags to filter by"),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """
    List documents for a project with pagination.
    """
    service = DocumentService(db)

    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]

    documents, total = await service.list(
        project_id=project_id,
        page=page,
        page_size=page_size,
        status=status,
        tags=tag_list,
    )

    summaries = [
        DocumentSummary(
            id=doc.id,
            project_id=doc.project_id,
            title=doc.title,
            authors=doc.authors or [],
            year=doc.year,
            doi=doc.doi,
            status=doc.status,
            is_open_access=doc.is_open_access,
            citation_count=doc.citation_count,
            has_summary=doc.summary is not None,
            has_full_text=doc.full_text is not None,
            chunk_count=doc.chunk_count,
            tags=doc.tags or [],
            relevance_score=doc.relevance_score,
            created_at=doc.created_at,
        )
        for doc in documents
    ]

    return DocumentListResponse(
        documents=summaries,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Get a document by ID.
    """
    service = DocumentService(db)
    try:
        document = await service.get(document_id)
        return DocumentResponse.model_validate(document)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    request: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Update a document.
    """
    service = DocumentService(db)
    try:
        document = await service.update(document_id, request)
        await db.commit()
        return DocumentResponse.model_validate(document)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a document.
    """
    service = DocumentService(db)
    try:
        await service.delete(document_id)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def get_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentChunkResponse]:
    """
    Get all chunks for a document.
    """
    service = DocumentService(db)
    chunks = await service.get_chunks(document_id)

    return [
        DocumentChunkResponse(
            id=chunk.id,
            document_id=chunk.document_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            section_type=chunk.section_type,
            section_title=chunk.section_title,
            token_count=chunk.token_count,
            char_count=chunk.char_count,
            has_embedding=chunk.embedding is not None,
            created_at=chunk.created_at,
        )
        for chunk in chunks
    ]


@router.post("/{document_id}/process", response_model=ProcessingStatus)
async def process_document(
    document_id: int,
    request: ProcessingRequest | None = None,
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
    chunk_size: int = Query(1000, ge=100, le=5000),
    chunk_overlap: int = Query(200, ge=0, le=500),
    db: AsyncSession = Depends(get_db),
) -> ProcessingStatus:
    """
    Process a document: chunk, embed, summarize, and extract.

    This triggers the full document processing pipeline.
    """
    if request is None:
        request = ProcessingRequest()

    try:
        # First, chunk and embed
        embedding_service = get_embedding_service(db)
        result = await embedding_service.process_document(
            document_id=document_id,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        has_summary = False
        has_evidence = False
        has_tags = False

        # Generate summary if requested
        if request.generate_summary:
            summarization_service = get_summarization_service(db)
            await summarization_service.process_document(
                document_id=document_id,
                extract_findings=request.extract_evidence,
                extract_evidence=request.extract_evidence,
            )
            has_summary = True
            has_evidence = request.extract_evidence

        # Auto-tag if requested
        if request.auto_tag:
            tagging_service = get_tagging_service(db)
            await tagging_service.auto_tag_document(document_id)
            has_tags = True

        await db.commit()

        return ProcessingStatus(
            document_id=document_id,
            status=DocumentStatus(result["status"]),
            chunk_count=result["chunks_created"],
            has_summary=has_summary,
            has_evidence=has_evidence,
            has_tags=has_tags,
            error_message=result.get("error"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{document_id}/summarize")
async def summarize_document(
    document_id: int,
    level: SummaryLevel = SummaryLevel.STANDARD,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate or regenerate a document summary.
    """
    try:
        service = get_summarization_service(db)
        doc_service = DocumentService(db)
        document = await doc_service.get(document_id)

        result = await service.summarize(document, level)
        await doc_service.set_summary(document_id, result.summary)
        await db.commit()

        return {
            "document_id": document_id,
            "summary": result.summary,
            "level": result.level.value,
            "model": result.model,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{document_id}/auto-tag")
async def auto_tag_document(
    document_id: int,
    use_ai: bool = True,
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Auto-generate tags for a document.
    """
    try:
        service = get_tagging_service(db)
        tags = await service.auto_tag_document(
            document_id=document_id,
            use_ai=use_ai,
            min_confidence=min_confidence,
        )

        return {
            "document_id": document_id,
            "tags": tags,
            "count": len(tags),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/stats/{project_id}")
async def get_document_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get document statistics for a project.
    """
    doc_service = DocumentService(db)
    retrieval_service = get_retrieval_service(db)

    counts = await doc_service.count_by_project(project_id)
    retrieval_stats = await retrieval_service.get_retrieval_stats(project_id)

    return {
        "project_id": project_id,
        "documents": counts,
        "retrieval": retrieval_stats,
    }


@router.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    project_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> SemanticSearchResponse:
    """
    Perform semantic search across documents.

    Uses vector similarity to find relevant content.
    """
    service = get_retrieval_service(db)

    response = await service.search(
        query=request.query,
        project_id=project_id,
        document_ids=request.document_ids,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        section_types=request.section_types,
    )

    results = [
        SimilarChunkResult(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            document_title=r.document_title,
            content=r.content,
            section_type=r.section_type,
            similarity_score=r.similarity_score,
        )
        for r in response.results
    ]

    return SemanticSearchResponse(
        query=response.query,
        results=results,
        total_results=response.total_results,
    )


@router.get("/{document_id}/related")
async def find_related_documents(
    document_id: int,
    project_id: int | None = None,
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Find documents related to the given document.
    """
    service = get_retrieval_service(db)
    related = await service.find_related_documents(
        document_id=document_id,
        project_id=project_id,
        top_k=top_k,
    )
    return related


@router.post("/advanced-search", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> AdvancedSearchResponse:
    """
    Advanced search with filters and facets.

    Supports filtering by:
    - Text query (keyword search in title/abstract)
    - Tags and keywords
    - Date range (years)
    - Authors and journals
    - Document types
    - Citation metrics
    - Open access, full text availability

    Returns results with optional facet counts for filtering UI.
    """
    service = AdvancedSearchService(db)

    try:
        return await service.search(
            project_id=request.project_id,
            filters=request.filters,
            page=request.page,
            page_size=request.page_size,
            include_facets=request.include_facets,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
