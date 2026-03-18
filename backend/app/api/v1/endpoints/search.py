"""Academic search endpoints."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas.paper import (
    AggregatedSearchResult,
    DocumentType,
    Paper,
    SearchFilters,
)
from app.sources import get_source_manager

router = APIRouter()


@router.get("/sources")
async def list_sources() -> dict:
    """
    List all available academic sources.

    Returns information about each source including
    its capabilities and rate limits.
    """
    manager = get_source_manager()
    return {
        "sources": manager.list_all_info(),
        "total": len(manager.list_sources()),
    }


@router.get("/sources/health")
async def check_sources_health() -> dict:
    """
    Check health status of all academic sources.
    """
    manager = get_source_manager()
    health = await manager.healthcheck_all()
    return {"sources": health}


@router.get("", response_model=AggregatedSearchResult)
async def search_papers(
    q: str = Query(..., min_length=2, description="Search query"),
    sources: str | None = Query(None, description="Comma-separated source names"),
    year_from: int | None = Query(None, ge=1900, le=2100, description="Start year"),
    year_to: int | None = Query(None, ge=1900, le=2100, description="End year"),
    open_access: bool = Query(False, description="Only open access papers"),
    min_citations: int = Query(0, ge=0, description="Minimum citation count"),
    document_types: str | None = Query(None, description="Comma-separated document types"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page per source"),
    deduplicate: bool = Query(True, description="Deduplicate results across sources"),
) -> AggregatedSearchResult:
    """
    Search for academic papers across multiple sources.

    Searches OpenAlex, Crossref, Semantic Scholar, arXiv, and PubMed
    concurrently and returns deduplicated results.

    Results are normalized to a common format regardless of source.
    """
    manager = get_source_manager()

    # Parse sources
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",")]
        # Validate source names
        available = manager.list_sources()
        invalid = [s for s in source_list if s not in available]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sources: {invalid}. Available: {available}",
            )

    # Parse document types
    doc_types = []
    if document_types:
        for dt in document_types.split(","):
            try:
                doc_types.append(DocumentType(dt.strip()))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document type: {dt}. Valid types: {[t.value for t in DocumentType]}",
                )

    # Build filters
    filters = SearchFilters(
        keywords=[q],
        year_from=year_from,
        year_to=year_to,
        open_access_only=open_access,
        min_citations=min_citations,
        document_types=doc_types,
    )

    # Execute search
    result = await manager.search(
        query=q,
        filters=filters,
        sources=source_list,
        page=page,
        page_size=page_size,
        deduplicate=deduplicate,
    )

    return result


@router.get("/doi/{doi:path}", response_model=Paper)
async def get_paper_by_doi(
    doi: str,
    sources: str | None = Query(None, description="Comma-separated source names to search"),
) -> Paper:
    """
    Look up a paper by its DOI.

    Searches across sources until the paper is found.
    """
    manager = get_source_manager()

    # Parse sources
    source_list = None
    if sources:
        source_list = [s.strip() for s in sources.split(",")]

    paper = await manager.get_by_doi(doi, source_list)

    if not paper:
        raise HTTPException(
            status_code=404,
            detail=f"Paper with DOI {doi} not found",
        )

    return paper


@router.get("/source/{source_name}")
async def search_single_source(
    source_name: str,
    q: str = Query(..., min_length=2, description="Search query"),
    year_from: int | None = Query(None, ge=1900, le=2100),
    year_to: int | None = Query(None, ge=1900, le=2100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """
    Search a specific academic source.

    Useful for testing individual sources or when you want
    results from only one source.
    """
    manager = get_source_manager()
    source = manager.get(source_name)

    if not source:
        available = manager.list_sources()
        raise HTTPException(
            status_code=404,
            detail=f"Source '{source_name}' not found. Available: {available}",
        )

    filters = SearchFilters(
        keywords=[q],
        year_from=year_from,
        year_to=year_to,
    )

    try:
        result = await source.search(q, filters, page, page_size)
        return {
            "source": source_name,
            "papers": [p.model_dump() for p in result.papers],
            "total_results": result.total_results,
            "page": result.page,
            "page_size": result.page_size,
            "has_more": result.has_more,
        }
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error searching {source_name}: {str(e)}",
        )
