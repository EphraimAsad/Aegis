"""Export endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.export import (
    EXPORT_CONTENT_TYPES,
    ExportFormat,
    ExportOptions,
    ExportPreviewRequest,
    ExportPreviewResponse,
    ExportRequest,
    ExportResponse,
)
from app.services.export import ExportService

router = APIRouter()


@router.post("", response_model=ExportResponse)
async def export_documents(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """
    Export documents from a project.

    Supports CSV, JSON, Markdown, BibTeX, and annotated bibliography formats.
    """
    service = ExportService(db)

    try:
        result = await service.export_documents(
            project_id=request.project_id,
            format=request.format,
            options=request.options,
            document_ids=request.document_ids,
            filename=request.filename,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/download")
async def download_export(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export and download documents as a file.

    Returns the export as a downloadable file with appropriate content type.
    """
    service = ExportService(db)

    try:
        result = await service.export_documents(
            project_id=request.project_id,
            format=request.format,
            options=request.options,
            document_ids=request.document_ids,
            filename=request.filename,
        )

        return Response(
            content=result.content,
            media_type=result.content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{result.filename}"',
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/preview", response_model=ExportPreviewResponse)
async def preview_export(
    project_id: int,
    format: ExportFormat = ExportFormat.CSV,
    limit: int = Query(default=5, ge=1, le=20),
    include_abstracts: bool = True,
    include_summaries: bool = True,
    db: AsyncSession = Depends(get_db),
) -> ExportPreviewResponse:
    """
    Preview an export before downloading.

    Returns a limited preview of the export content.
    """
    service = ExportService(db)

    options = ExportOptions(
        include_abstracts=include_abstracts,
        include_summaries=include_summaries,
    )

    try:
        preview, total, preview_count = await service.preview_export(
            project_id=project_id,
            format=format,
            options=options,
            limit=limit,
        )

        return ExportPreviewResponse(
            preview=preview,
            total_documents=total,
            preview_count=preview_count,
            format=format,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/formats")
async def list_export_formats() -> dict:
    """
    List available export formats.

    Returns information about each supported export format.
    """
    formats = []
    for fmt in ExportFormat:
        formats.append({
            "id": fmt.value,
            "name": fmt.name.replace("_", " ").title(),
            "content_type": EXPORT_CONTENT_TYPES[fmt],
            "description": _get_format_description(fmt),
        })

    return {"formats": formats}


def _get_format_description(fmt: ExportFormat) -> str:
    """Get description for an export format."""
    descriptions = {
        ExportFormat.CSV: "Comma-separated values, compatible with spreadsheets",
        ExportFormat.JSON: "JavaScript Object Notation, structured data format",
        ExportFormat.MARKDOWN: "Formatted text document with metadata and summaries",
        ExportFormat.BIBTEX: "LaTeX bibliography format for academic papers",
        ExportFormat.ANNOTATED_BIBLIOGRAPHY: "Formatted bibliography with annotations and key findings",
    }
    return descriptions.get(fmt, "")
