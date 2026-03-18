"""Citation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.citation import (
    CitationRequest,
    CitationResponse,
    CitationStyle,
    CitationStylesResponse,
    DocumentCitations,
)
from app.services.citation import CitationService

router = APIRouter()


@router.post("/format", response_model=CitationResponse)
async def format_citations(
    request: CitationRequest,
    db: AsyncSession = Depends(get_db),
) -> CitationResponse:
    """
    Format citations for multiple documents.

    Formats citations in the specified style (APA, Chicago, MLA, Harvard, IEEE, BibTeX).
    """
    service = CitationService(db)

    try:
        result = await service.format_citations(
            document_ids=request.document_ids,
            style=request.style,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/document/{document_id}", response_model=DocumentCitations)
async def get_document_citations(
    document_id: int,
    styles: str | None = Query(
        default=None,
        description="Comma-separated list of styles (e.g., 'apa,chicago,bibtex')",
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentCitations:
    """
    Get citations for a single document in all or specified styles.

    If no styles are specified, returns citations in all available styles.
    """
    service = CitationService(db)

    # Parse styles parameter
    style_list = None
    if styles:
        try:
            style_list = [CitationStyle(s.strip().lower()) for s in styles.split(",")]
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid style. Available styles: {[s.value for s in CitationStyle]}",
            )

    try:
        result = await service.get_document_citations(
            document_id=document_id,
            styles=style_list,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/styles", response_model=CitationStylesResponse)
async def list_citation_styles() -> CitationStylesResponse:
    """
    List available citation styles.

    Returns information about each supported citation style with examples.
    """
    # We don't need a db session for this static data
    from app.services.citation import CitationService
    from app.db.session import get_db

    # Create a service with a mock session just to get styles
    # Actually, get_available_styles doesn't need db, but service requires it
    # Let's just return the styles directly
    from app.schemas.citation import CITATION_STYLES_INFO

    return CitationStylesResponse(styles=CITATION_STYLES_INFO)
