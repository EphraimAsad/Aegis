"""Service for analytics and insights."""

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.schemas.analytics import (
    AnalyticsDashboard,
    AnalyticsOverview,
    AuthorStats,
    DocumentTypeStats,
    KeywordStats,
    PublicationTrend,
    SourceStats,
)


class AnalyticsService:
    """Service for computing analytics and insights."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def get_overview(self, project_id: int) -> AnalyticsOverview:
        """
        Get overview statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            AnalyticsOverview
        """
        # Get all documents
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        documents = list(result.scalars().all())

        if not documents:
            return AnalyticsOverview(project_id=project_id)

        # Compute statistics
        status_counts = Counter(
            doc.status.value if hasattr(doc.status, "value") else doc.status
            for doc in documents
        )
        year_counts = Counter(doc.year for doc in documents if doc.year)

        total_citations = sum(doc.citation_count or 0 for doc in documents)
        docs_with_citations = [doc for doc in documents if doc.citation_count]
        avg_citations = (
            total_citations / len(docs_with_citations) if docs_with_citations else 0
        )

        # Count unique authors
        authors = set()
        for doc in documents:
            if doc.authors:
                for author in doc.authors:
                    if isinstance(author, dict):
                        authors.add(author.get("name", ""))
                    else:
                        authors.add(str(author))

        # Count unique journals
        journals = set()
        for doc in documents:
            if doc.journal and isinstance(doc.journal, dict):
                journal_name = doc.journal.get("name", "")
                if journal_name:
                    journals.add(journal_name)

        # Count documents with features
        open_access_count = sum(1 for doc in documents if doc.is_open_access)
        preprint_count = sum(1 for doc in documents if doc.is_preprint)
        with_full_text = sum(1 for doc in documents if doc.full_text)
        with_summary = sum(1 for doc in documents if doc.summary)

        # Compute embedding coverage
        ready_docs = [doc for doc in documents if doc.status == DocumentStatus.READY]
        docs_with_chunks = sum(1 for doc in ready_docs if doc.chunk_count > 0)
        embedding_coverage = docs_with_chunks / len(ready_docs) if ready_docs else 0

        return AnalyticsOverview(
            project_id=project_id,
            total_documents=len(documents),
            documents_by_status=dict(status_counts),
            documents_by_year=dict(sorted(year_counts.items())),
            total_citations=total_citations,
            avg_citations=round(avg_citations, 2),
            unique_authors=len(authors),
            unique_journals=len(journals),
            open_access_count=open_access_count,
            preprint_count=preprint_count,
            documents_with_full_text=with_full_text,
            documents_with_summary=with_summary,
            embedding_coverage=round(embedding_coverage * 100, 1),
        )

    async def get_publication_trends(
        self,
        project_id: int,
        from_year: int | None = None,
        to_year: int | None = None,
    ) -> list[PublicationTrend]:
        """
        Get publication trends over time.

        Args:
            project_id: Project ID
            from_year: Start year (optional)
            to_year: End year (optional)

        Returns:
            List of PublicationTrend
        """
        query = select(Document).where(
            Document.project_id == project_id,
            Document.year.isnot(None),
        )

        if from_year:
            query = query.where(Document.year >= from_year)
        if to_year:
            query = query.where(Document.year <= to_year)

        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        # Group by year
        year_data: defaultdict[int, dict[str, int]] = defaultdict(
            lambda: {
                "count": 0,
                "citations": 0,
                "open_access": 0,
            }
        )

        for doc in documents:
            year = doc.year
            if year is None:
                continue
            year_data[year]["count"] += 1
            year_data[year]["citations"] += doc.citation_count or 0
            if doc.is_open_access:
                year_data[year]["open_access"] += 1

        # Convert to trends
        trends = []
        for year in sorted(year_data.keys()):
            data = year_data[year]
            trends.append(
                PublicationTrend(
                    year=year,
                    count=data["count"],
                    citation_total=data["citations"],
                    citation_avg=(
                        round(data["citations"] / data["count"], 2)
                        if data["count"]
                        else 0
                    ),
                    open_access_count=data["open_access"],
                )
            )

        return trends

    async def get_top_authors(
        self,
        project_id: int,
        limit: int = 20,
    ) -> tuple[list[AuthorStats], int]:
        """
        Get top authors by document count.

        Args:
            project_id: Project ID
            limit: Max authors to return

        Returns:
            Tuple of (author stats list, total unique authors)
        """
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        documents = list(result.scalars().all())

        # Collect author data
        author_data: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "citations": 0,
                "years": [],
                "affiliations": set(),
            }
        )

        for doc in documents:
            if not doc.authors:
                continue

            for author in doc.authors:
                if isinstance(author, dict):
                    name = author.get("name", "")
                    affiliations = author.get("affiliations", [])
                else:
                    name = str(author)
                    affiliations = []

                if name:
                    author_data[name]["count"] += 1
                    author_data[name]["citations"] += doc.citation_count or 0
                    if doc.year:
                        author_data[name]["years"].append(doc.year)
                    for aff in affiliations:
                        if isinstance(aff, str):
                            author_data[name]["affiliations"].add(aff)

        # Convert to stats and sort
        author_stats = []
        for name, data in author_data.items():
            years = data["years"]
            author_stats.append(
                AuthorStats(
                    name=name,
                    document_count=data["count"],
                    total_citations=data["citations"],
                    first_year=min(years) if years else None,
                    last_year=max(years) if years else None,
                    affiliations=list(data["affiliations"])[:5],
                )
            )

        # Sort by document count
        author_stats.sort(key=lambda x: x.document_count, reverse=True)

        return author_stats[:limit], len(author_data)

    async def get_keywords_and_tags(
        self,
        project_id: int,
        limit: int = 50,
    ) -> tuple[list[KeywordStats], list[KeywordStats]]:
        """
        Get top keywords and tags.

        Args:
            project_id: Project ID
            limit: Max items to return

        Returns:
            Tuple of (keywords, tags)
        """
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        documents = list(result.scalars().all())

        # Count keywords and tags
        keyword_counts: Counter[str] = Counter()
        tag_counts: Counter[str] = Counter()

        for doc in documents:
            if doc.keywords:
                for kw in doc.keywords:
                    keyword_counts[kw] += 1
            if doc.tags:
                for tag in doc.tags:
                    tag_counts[tag] += 1

        # Convert to stats
        keywords = [
            KeywordStats(keyword=kw, count=count)
            for kw, count in keyword_counts.most_common(limit)
        ]

        tags = [
            KeywordStats(keyword=tag, count=count)
            for tag, count in tag_counts.most_common(limit)
        ]

        return keywords, tags

    async def get_source_distribution(
        self,
        project_id: int,
    ) -> list[SourceStats]:
        """
        Get document distribution by source.

        Args:
            project_id: Project ID

        Returns:
            List of SourceStats
        """
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        documents = list(result.scalars().all())

        # Group by source
        source_data: defaultdict[str, dict[str, int]] = defaultdict(
            lambda: {"count": 0, "citations": 0}
        )

        for doc in documents:
            source = doc.source_name or "unknown"
            source_data[source]["count"] += 1
            source_data[source]["citations"] += doc.citation_count or 0

        # Convert to stats
        stats = []
        for source, data in source_data.items():
            stats.append(
                SourceStats(
                    source_name=source,
                    document_count=data["count"],
                    avg_citations=(
                        round(data["citations"] / data["count"], 2)
                        if data["count"]
                        else 0
                    ),
                )
            )

        # Sort by count
        stats.sort(key=lambda x: x.document_count, reverse=True)

        return stats

    async def get_document_type_distribution(
        self,
        project_id: int,
    ) -> list[DocumentTypeStats]:
        """
        Get document distribution by type.

        Args:
            project_id: Project ID

        Returns:
            List of DocumentTypeStats
        """
        result = await self.db.execute(
            select(Document).where(Document.project_id == project_id)
        )
        documents = list(result.scalars().all())

        # Count by type
        type_counts = Counter(doc.document_type or "unknown" for doc in documents)
        total = len(documents)

        # Convert to stats
        stats = []
        for doc_type, count in type_counts.most_common():
            stats.append(
                DocumentTypeStats(
                    document_type=doc_type,
                    count=count,
                    percentage=round(count / total * 100, 1) if total else 0,
                )
            )

        return stats

    async def get_dashboard(self, project_id: int) -> AnalyticsDashboard:
        """
        Get complete dashboard data.

        Args:
            project_id: Project ID

        Returns:
            AnalyticsDashboard
        """
        overview = await self.get_overview(project_id)
        trends = await self.get_publication_trends(project_id)
        authors, _ = await self.get_top_authors(project_id, limit=10)
        keywords, tags = await self.get_keywords_and_tags(project_id, limit=20)
        sources = await self.get_source_distribution(project_id)
        doc_types = await self.get_document_type_distribution(project_id)

        return AnalyticsDashboard(
            overview=overview,
            publication_trends=trends,
            top_authors=authors,
            top_keywords=keywords,
            top_tags=tags,
            source_distribution=sources,
            document_type_distribution=doc_types,
        )


def get_analytics_service(db: AsyncSession) -> AnalyticsService:
    """Get an analytics service instance."""
    return AnalyticsService(db)
