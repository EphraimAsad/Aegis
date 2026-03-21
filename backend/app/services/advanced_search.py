"""Service for advanced document search with filters."""

from collections import Counter
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.schemas.advanced_search import (
    AdvancedSearchFilters,
    AdvancedSearchResponse,
    SearchFacets,
)
from app.schemas.document import DocumentSummary


class AdvancedSearchService:
    """Service for advanced document search."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def search(
        self,
        project_id: int,
        filters: AdvancedSearchFilters,
        page: int = 1,
        page_size: int = 20,
        include_facets: bool = True,
        sort_by: str = "relevance",
        sort_order: str = "desc",
    ) -> AdvancedSearchResponse:
        """
        Search documents with advanced filters.

        Args:
            project_id: Project ID
            filters: Search filters
            page: Page number
            page_size: Results per page
            include_facets: Whether to include facet counts
            sort_by: Sort field
            sort_order: Sort order

        Returns:
            AdvancedSearchResponse
        """
        # Build base query
        query = select(Document).where(Document.project_id == project_id)

        # Apply filters
        query = self._apply_filters(query, filters)

        # Get total count before pagination
        count_query = select(func.count(Document.id)).where(
            Document.project_id == project_id
        )
        count_query = self._apply_filters(count_query, filters)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        query = self._apply_sorting(query, sort_by, sort_order, filters)

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        # Convert to summaries
        summaries = [self._to_summary(doc) for doc in documents]

        # Compute facets if requested
        facets = None
        if include_facets:
            facets = await self._compute_facets(project_id, filters)

        return AdvancedSearchResponse(
            documents=summaries,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total,
            facets=facets,
            query_used=filters.query,
        )

    def _apply_filters(self, query: Any, filters: AdvancedSearchFilters) -> Any:
        """Apply all filters to query."""
        # Text search (keyword in title or abstract)
        if filters.query:
            search_term = f"%{filters.query}%"
            query = query.where(
                or_(
                    Document.title.ilike(search_term),
                    Document.abstract.ilike(search_term),
                )
            )

        # Date filter
        if filters.date_filter:
            if filters.date_filter.from_year:
                query = query.where(Document.year >= filters.date_filter.from_year)
            if filters.date_filter.to_year:
                query = query.where(Document.year <= filters.date_filter.to_year)

        # Tags filter
        if filters.tags:
            for tag in filters.tags:
                query = query.where(Document.tags.any(tag))  # type: ignore[arg-type]

        # Exclude tags
        if filters.exclude_tags:
            for tag in filters.exclude_tags:
                query = query.where(~Document.tags.any(tag))  # type: ignore[arg-type]

        # Keywords filter
        if filters.keywords:
            for keyword in filters.keywords:
                query = query.where(Document.keywords.any(keyword))  # type: ignore[arg-type]

        # Authors filter (partial match in JSONB)
        if filters.authors:
            author_conditions = []
            for author in filters.authors:
                # Search in authors JSONB array
                author_conditions.append(
                    Document.authors.cast(str).ilike(f"%{author}%")
                )
            if author_conditions:
                query = query.where(or_(*author_conditions))

        # Journals filter (partial match)
        if filters.journals:
            journal_conditions = []
            for journal in filters.journals:
                journal_conditions.append(
                    Document.journal.cast(str).ilike(f"%{journal}%")
                )
            if journal_conditions:
                query = query.where(or_(*journal_conditions))

        # Document types filter
        if filters.document_types:
            query = query.where(Document.document_type.in_(filters.document_types))

        # Status filter
        if filters.statuses:
            query = query.where(Document.status.in_(filters.statuses))
        else:
            # Default to ready documents
            query = query.where(Document.status == DocumentStatus.READY)

        # Metrics filter
        if filters.metrics_filter:
            if filters.metrics_filter.min_citations is not None:
                query = query.where(
                    Document.citation_count >= filters.metrics_filter.min_citations
                )
            if filters.metrics_filter.max_citations is not None:
                query = query.where(
                    Document.citation_count <= filters.metrics_filter.max_citations
                )

        # Boolean flags
        if filters.open_access_only:
            query = query.where(Document.is_open_access.is_(True))

        if filters.has_full_text is not None:
            if filters.has_full_text:
                query = query.where(Document.full_text.isnot(None))
            else:
                query = query.where(Document.full_text.is_(None))

        if filters.has_summary is not None:
            if filters.has_summary:
                query = query.where(Document.summary.isnot(None))
            else:
                query = query.where(Document.summary.is_(None))

        if filters.exclude_preprints:
            query = query.where(Document.is_preprint.is_(False))

        if filters.exclude_retracted:
            query = query.where(Document.is_retracted.is_(False))

        # Sources filter
        if filters.sources:
            query = query.where(Document.source_name.in_(filters.sources))

        return query

    def _apply_sorting(
        self,
        query: Any,
        sort_by: str,
        sort_order: str,
        filters: AdvancedSearchFilters,
    ) -> Any:
        """Apply sorting to query."""
        desc = sort_order.lower() == "desc"
        order_col: Any

        if sort_by == "year":
            order_col = Document.year.desc() if desc else Document.year.asc()
            query = query.order_by(order_col.nullslast())
        elif sort_by == "citations":
            order_col = (
                Document.citation_count.desc()
                if desc
                else Document.citation_count.asc()
            )
            query = query.order_by(order_col.nullslast())
        elif sort_by == "title":
            order_col = Document.title.desc() if desc else Document.title.asc()
            query = query.order_by(order_col)
        elif sort_by == "created":
            order_col = (
                Document.created_at.desc() if desc else Document.created_at.asc()
            )
            query = query.order_by(order_col)
        else:
            # Default: relevance (by year descending, then citation count)
            query = query.order_by(
                Document.year.desc().nullslast(),
                Document.citation_count.desc().nullslast(),
            )

        return query

    async def _compute_facets(
        self,
        project_id: int,
        filters: AdvancedSearchFilters,
    ) -> SearchFacets:
        """Compute facet counts for search results."""
        # Get all matching documents for facet computation
        query = select(Document).where(
            Document.project_id == project_id,
            Document.status == DocumentStatus.READY,
        )

        # Apply filters but exclude facet-specific filters to show all options
        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        # Compute facets
        years: Counter[int] = Counter()
        authors: Counter[str] = Counter()
        journals: Counter[str] = Counter()
        tags: Counter[str] = Counter()
        document_types: Counter[str] = Counter()
        sources: Counter[str] = Counter()

        for doc in documents:
            # Years
            if doc.year:
                years[doc.year] += 1

            # Authors (extract names)
            if doc.authors:
                for author in doc.authors:
                    if isinstance(author, dict):
                        name = author.get("name", "")
                    else:
                        name = str(author)
                    if name:
                        authors[name] += 1

            # Journals
            if doc.journal and isinstance(doc.journal, dict):
                journal_name = doc.journal.get("name", "")
                if journal_name:
                    journals[journal_name] += 1

            # Tags
            if doc.tags:
                for tag in doc.tags:
                    tags[tag] += 1

            # Document types
            if doc.document_type:
                document_types[doc.document_type] += 1

            # Sources
            if doc.source_name:
                sources[doc.source_name] += 1

        return SearchFacets(
            years=dict(sorted(years.items(), reverse=True)),
            authors=dict(authors.most_common(50)),
            journals=dict(journals.most_common(30)),
            tags=dict(tags.most_common(50)),
            document_types=dict(document_types.most_common(20)),
            sources=dict(sources.most_common(10)),
        )

    def _to_summary(self, doc: Document) -> DocumentSummary:
        """Convert document to summary."""
        return DocumentSummary(
            id=doc.id,
            title=doc.title,
            authors=self._format_authors(doc.authors),
            year=doc.year,
            doi=doc.doi,
            status=doc.status,
            document_type=doc.document_type,
            journal_name=self._get_journal_name(doc.journal),
            citation_count=doc.citation_count,
            is_open_access=doc.is_open_access,
            has_full_text=doc.full_text is not None,
            has_summary=doc.summary is not None,
            tags=doc.tags or [],
            source_name=doc.source_name,
            created_at=doc.created_at,
        )

    def _format_authors(self, authors: list | None) -> str:
        """Format authors as a simple string."""
        if not authors:
            return ""

        names = []
        for author in authors[:3]:
            if isinstance(author, dict):
                names.append(author.get("name", "Unknown"))
            elif isinstance(author, str):
                names.append(author)

        if len(authors) > 3:
            return f"{names[0]} et al."
        return ", ".join(names)

    def _get_journal_name(self, journal: dict | None) -> str | None:
        """Extract journal name."""
        if not journal or not isinstance(journal, dict):
            return None
        return journal.get("name")


def get_advanced_search_service(db: AsyncSession) -> AdvancedSearchService:
    """Get an advanced search service instance."""
    return AdvancedSearchService(db)
