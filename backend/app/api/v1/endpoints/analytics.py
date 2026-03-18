"""Analytics endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsAuthors,
    AnalyticsDashboard,
    AnalyticsKeywords,
    AnalyticsOverview,
    AnalyticsTrends,
)
from app.services.analytics import AnalyticsService

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverview:
    """
    Get overview statistics for a project.

    Returns counts, averages, and distribution data.
    """
    service = AnalyticsService(db)

    try:
        return await service.get_overview(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsDashboard:
    """
    Get complete analytics dashboard data.

    Returns overview, trends, top authors, keywords, and distributions.
    """
    service = AnalyticsService(db)

    try:
        return await service.get_dashboard(project_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/trends", response_model=AnalyticsTrends)
async def get_publication_trends(
    project_id: int,
    from_year: int | None = Query(default=None, description="Start year"),
    to_year: int | None = Query(default=None, description="End year"),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsTrends:
    """
    Get publication trends over time.

    Returns document counts and citation statistics by year.
    """
    service = AnalyticsService(db)

    try:
        trends = await service.get_publication_trends(
            project_id=project_id,
            from_year=from_year,
            to_year=to_year,
        )
        return AnalyticsTrends(
            project_id=project_id,
            trends=trends,
            from_year=from_year,
            to_year=to_year,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/authors", response_model=AnalyticsAuthors)
async def get_top_authors(
    project_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsAuthors:
    """
    Get top authors by document count.

    Returns author statistics including citation counts and affiliations.
    """
    service = AnalyticsService(db)

    try:
        authors, total = await service.get_top_authors(
            project_id=project_id,
            limit=limit,
        )
        return AnalyticsAuthors(
            project_id=project_id,
            authors=authors,
            total_unique_authors=total,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/keywords", response_model=AnalyticsKeywords)
async def get_keywords(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsKeywords:
    """
    Get top keywords and tags.

    Returns keyword and tag frequency data.
    """
    service = AnalyticsService(db)

    try:
        keywords, tags = await service.get_keywords_and_tags(
            project_id=project_id,
            limit=limit,
        )
        return AnalyticsKeywords(
            project_id=project_id,
            keywords=keywords,
            tags=tags,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
