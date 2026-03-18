"""Crossref source adapter.

Crossref is a registration agency for scholarly content DOIs.
API Documentation: https://api.crossref.org/swagger-ui/index.html
"""

from datetime import date
from typing import Any

from app.schemas.paper import (
    Author,
    DocumentType,
    Identifier,
    Journal,
    Paper,
    PaperSearchResult,
    SearchFilters,
)
from app.sources.base import BaseSourceAdapter, SourceCapabilities


class CrossrefAdapter(BaseSourceAdapter):
    """
    Crossref source adapter.

    Crossref provides access to metadata for DOI-registered works,
    including citation counts and references.
    """

    def __init__(
        self,
        email: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Crossref adapter.

        Args:
            email: Email for polite pool (required for higher rate limits)
            timeout: Request timeout
            max_retries: Max retries for failed requests
        """
        super().__init__(timeout, max_retries)
        self._email = email

    def _get_headers(self) -> dict[str, str]:
        headers = super()._get_headers()
        if self._email:
            headers["User-Agent"] = f"Aegis/0.1.0 (mailto:{self._email})"
        return headers

    @property
    def name(self) -> str:
        return "crossref"

    @property
    def display_name(self) -> str:
        return "Crossref"

    @property
    def base_url(self) -> str:
        return "https://api.crossref.org"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_fulltext_search=True,
            supports_title_search=True,
            supports_author_search=True,
            supports_doi_lookup=True,
            supports_date_filter=True,
            supports_citation_filter=False,
            supports_open_access_filter=False,
            supports_pagination=True,
            max_results_per_request=100,
            rate_limit_per_second=50.0 if self._email else 1.0,
            requires_api_key=False,
        )

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperSearchResult:
        """Search Crossref for papers."""
        params: dict[str, Any] = {
            "query": query,
            "rows": min(page_size, self.capabilities.max_results_per_request),
            "offset": (page - 1) * page_size,
        }

        # Add filters
        filter_parts = []

        if filters:
            if filters.year_from:
                filter_parts.append(f"from-pub-date:{filters.year_from}")
            if filters.year_to:
                filter_parts.append(f"until-pub-date:{filters.year_to}")
            if filters.document_types:
                types = [self._map_document_type(t) for t in filters.document_types]
                for t in types:
                    filter_parts.append(f"type:{t}")

        if filter_parts:
            params["filter"] = ",".join(filter_parts)

        # Add email for polite pool
        if self._email:
            params["mailto"] = self._email

        try:
            data = await self._make_request("GET", f"{self.base_url}/works", params=params)
            message = data.get("message", {})

            papers = [self._normalize_paper(item) for item in message.get("items", [])]
            total = message.get("total-results", 0)

            return PaperSearchResult(
                papers=papers,
                total_results=total,
                query=query,
                source=self.name,
                page=page,
                page_size=page_size,
                has_more=page * page_size < total,
            )
        except Exception:
            return PaperSearchResult(
                papers=[],
                total_results=0,
                query=query,
                source=self.name,
                page=page,
                page_size=page_size,
                has_more=False,
            )

    async def get_by_doi(self, doi: str) -> Paper | None:
        """Get a paper by DOI from Crossref."""
        try:
            params = {}
            if self._email:
                params["mailto"] = self._email

            data = await self._make_request(
                "GET",
                f"{self.base_url}/works/{doi}",
                params=params,
            )
            return self._normalize_paper(data.get("message", {}))
        except Exception:
            return None

    async def get_by_id(self, source_id: str) -> Paper | None:
        """Get a paper by DOI (Crossref uses DOI as ID)."""
        return await self.get_by_doi(source_id)

    def _normalize_paper(self, raw: dict[str, Any]) -> Paper:
        """Convert Crossref work to normalized Paper."""
        # Extract authors
        authors = []
        for author_data in raw.get("author", []):
            name_parts = []
            if author_data.get("given"):
                name_parts.append(author_data["given"])
            if author_data.get("family"):
                name_parts.append(author_data["family"])

            affiliations = [
                aff.get("name", "")
                for aff in author_data.get("affiliation", [])
                if aff.get("name")
            ]

            authors.append(Author(
                name=" ".join(name_parts) if name_parts else "Unknown",
                given_name=author_data.get("given"),
                family_name=author_data.get("family"),
                orcid=author_data.get("ORCID"),
                affiliations=affiliations,
            ))

        # Extract publication date
        pub_date = None
        year = None
        date_parts = raw.get("published-print", raw.get("published-online", {})).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            year = parts[0] if len(parts) > 0 else None
            if len(parts) >= 3:
                try:
                    pub_date = date(parts[0], parts[1], parts[2])
                except ValueError:
                    pass

        # Extract journal info
        journal = None
        if raw.get("container-title"):
            journal = Journal(
                name=raw["container-title"][0] if raw["container-title"] else None,
                issn=raw.get("ISSN", [None])[0] if raw.get("ISSN") else None,
                volume=raw.get("volume"),
                issue=raw.get("issue"),
                pages=raw.get("page"),
                publisher=raw.get("publisher"),
            )

        # Build identifiers
        identifiers = []
        if raw.get("DOI"):
            identifiers.append(Identifier(type="doi", value=raw["DOI"]))
        if raw.get("ISSN"):
            for issn in raw["ISSN"]:
                identifiers.append(Identifier(type="issn", value=issn))

        # Determine document type
        doc_type = self._parse_document_type(raw.get("type", ""))

        # Extract subjects
        subjects = raw.get("subject", [])

        # Build paper
        paper = Paper(
            title=raw.get("title", ["Untitled"])[0] if raw.get("title") else "Untitled",
            abstract=raw.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", "") if raw.get("abstract") else None,
            authors=authors,
            document_type=doc_type,
            publication_date=pub_date,
            year=year,
            journal=journal,
            language=raw.get("language"),
            doi=raw.get("DOI"),
            identifiers=identifiers,
            url=raw.get("URL"),
            citation_count=raw.get("is-referenced-by-count"),
            reference_count=raw.get("references-count"),
            subjects=subjects,
            is_open_access=False,  # Crossref doesn't provide this directly
            is_preprint=doc_type == DocumentType.PREPRINT,
        )

        # Add source info
        paper.add_source(self._create_source_info(
            source_id=raw.get("DOI", ""),
            url=raw.get("URL"),
        ))

        paper.dedupe_key = paper.generate_dedupe_key()
        return paper

    def _parse_document_type(self, type_str: str) -> DocumentType:
        """Parse Crossref type to DocumentType enum."""
        mapping = {
            "journal-article": DocumentType.JOURNAL_ARTICLE,
            "proceedings-article": DocumentType.CONFERENCE_PAPER,
            "book": DocumentType.BOOK,
            "book-chapter": DocumentType.BOOK_CHAPTER,
            "dissertation": DocumentType.DISSERTATION,
            "dataset": DocumentType.DATASET,
            "posted-content": DocumentType.PREPRINT,
            "report": DocumentType.REPORT,
        }
        return mapping.get(type_str.lower(), DocumentType.OTHER)

    def _map_document_type(self, doc_type: DocumentType) -> str:
        """Map DocumentType enum to Crossref type string."""
        mapping = {
            DocumentType.JOURNAL_ARTICLE: "journal-article",
            DocumentType.CONFERENCE_PAPER: "proceedings-article",
            DocumentType.BOOK: "book",
            DocumentType.BOOK_CHAPTER: "book-chapter",
            DocumentType.DISSERTATION: "dissertation",
            DocumentType.PREPRINT: "posted-content",
        }
        return mapping.get(doc_type, "journal-article")
