"""Semantic Scholar source adapter.

Semantic Scholar is a free AI-powered research tool for scientific literature.
API Documentation: https://api.semanticscholar.org/api-docs/
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


class SemanticScholarAdapter(BaseSourceAdapter):
    """
    Semantic Scholar source adapter.

    Provides access to Semantic Scholar's corpus of scientific papers
    with AI-powered features like citation contexts and influential citations.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Semantic Scholar adapter.

        Args:
            api_key: Optional API key for higher rate limits
            timeout: Request timeout
            max_retries: Max retries for failed requests
        """
        super().__init__(timeout, max_retries)
        self._api_key = api_key

    def _get_headers(self) -> dict[str, str]:
        headers = super()._get_headers()
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    @property
    def name(self) -> str:
        return "semantic_scholar"

    @property
    def display_name(self) -> str:
        return "Semantic Scholar"

    @property
    def base_url(self) -> str:
        return "https://api.semanticscholar.org/graph/v1"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_fulltext_search=True,
            supports_title_search=True,
            supports_author_search=True,
            supports_doi_lookup=True,
            supports_date_filter=True,
            supports_citation_filter=True,
            supports_open_access_filter=True,
            supports_pagination=True,
            max_results_per_request=100,
            rate_limit_per_second=100.0 if self._api_key else 1.0,
            requires_api_key=False,
        )

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperSearchResult:
        """Search Semantic Scholar for papers."""
        # Fields to retrieve
        fields = "paperId,title,abstract,authors,year,venue,publicationDate,citationCount,referenceCount,isOpenAccess,openAccessPdf,externalIds,fieldsOfStudy,publicationTypes"

        params: dict[str, Any] = {
            "query": query,
            "fields": fields,
            "limit": min(page_size, self.capabilities.max_results_per_request),
            "offset": (page - 1) * page_size,
        }

        # Add filters
        if filters:
            if filters.year_from or filters.year_to:
                year_filter = ""
                if filters.year_from:
                    year_filter = str(filters.year_from)
                year_filter += "-"
                if filters.year_to:
                    year_filter += str(filters.year_to)
                params["year"] = year_filter

            if filters.open_access_only:
                params["openAccessPdf"] = ""

            if filters.min_citations > 0:
                params["minCitationCount"] = filters.min_citations

            if filters.subjects:
                params["fieldsOfStudy"] = ",".join(filters.subjects)

        try:
            data = await self._make_request(
                "GET",
                f"{self.base_url}/paper/search",
                params=params,
            )

            papers = [self._normalize_paper(item) for item in data.get("data", [])]
            total = data.get("total", 0)

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
        """Get a paper by DOI from Semantic Scholar."""
        try:
            fields = "paperId,title,abstract,authors,year,venue,publicationDate,citationCount,referenceCount,isOpenAccess,openAccessPdf,externalIds,fieldsOfStudy,publicationTypes"

            data = await self._make_request(
                "GET",
                f"{self.base_url}/paper/DOI:{doi}",
                params={"fields": fields},
            )
            return self._normalize_paper(data)
        except Exception:
            return None

    async def get_by_id(self, source_id: str) -> Paper | None:
        """Get a paper by Semantic Scholar paper ID."""
        try:
            fields = "paperId,title,abstract,authors,year,venue,publicationDate,citationCount,referenceCount,isOpenAccess,openAccessPdf,externalIds,fieldsOfStudy,publicationTypes"

            data = await self._make_request(
                "GET",
                f"{self.base_url}/paper/{source_id}",
                params={"fields": fields},
            )
            return self._normalize_paper(data)
        except Exception:
            return None

    def _normalize_paper(self, raw: dict[str, Any]) -> Paper:
        """Convert Semantic Scholar paper to normalized Paper."""
        # Extract authors
        authors = []
        for author_data in raw.get("authors", []):
            authors.append(Author(
                name=author_data.get("name", "Unknown"),
                affiliations=[],
            ))

        # Extract publication date
        pub_date = None
        year = raw.get("year")
        if raw.get("publicationDate"):
            try:
                pub_date = date.fromisoformat(raw["publicationDate"])
            except ValueError:
                pass

        # Extract journal/venue info
        journal = None
        if raw.get("venue"):
            journal = Journal(name=raw["venue"])

        # Build identifiers
        identifiers = []
        external_ids = raw.get("externalIds", {})
        if external_ids.get("DOI"):
            identifiers.append(Identifier(type="doi", value=external_ids["DOI"]))
        if external_ids.get("ArXiv"):
            identifiers.append(Identifier(type="arxiv", value=external_ids["ArXiv"]))
        if external_ids.get("PubMed"):
            identifiers.append(Identifier(type="pmid", value=external_ids["PubMed"]))
        if external_ids.get("CorpusId"):
            identifiers.append(Identifier(type="s2", value=str(external_ids["CorpusId"])))

        # Determine document type
        pub_types = raw.get("publicationTypes", [])
        doc_type = self._parse_document_type(pub_types)

        # Extract subjects
        subjects = raw.get("fieldsOfStudy", []) or []

        # Get open access PDF URL
        oa_pdf = raw.get("openAccessPdf", {})
        pdf_url = oa_pdf.get("url") if oa_pdf else None

        # Build paper
        paper = Paper(
            title=raw.get("title", "Untitled"),
            abstract=raw.get("abstract"),
            authors=authors,
            document_type=doc_type,
            publication_date=pub_date,
            year=year,
            journal=journal,
            doi=external_ids.get("DOI"),
            identifiers=identifiers,
            url=f"https://www.semanticscholar.org/paper/{raw.get('paperId', '')}",
            pdf_url=pdf_url,
            open_access_url=pdf_url,
            citation_count=raw.get("citationCount"),
            reference_count=raw.get("referenceCount"),
            subjects=subjects,
            is_open_access=raw.get("isOpenAccess", False),
            is_preprint="Preprint" in pub_types if pub_types else False,
        )

        # Add source info
        paper.add_source(self._create_source_info(
            source_id=raw.get("paperId", ""),
            url=f"https://www.semanticscholar.org/paper/{raw.get('paperId', '')}",
        ))

        paper.dedupe_key = paper.generate_dedupe_key()
        return paper

    def _parse_document_type(self, pub_types: list[str]) -> DocumentType:
        """Parse Semantic Scholar publication types to DocumentType."""
        if not pub_types:
            return DocumentType.OTHER

        type_str = pub_types[0].lower()
        mapping = {
            "journalarticle": DocumentType.JOURNAL_ARTICLE,
            "conference": DocumentType.CONFERENCE_PAPER,
            "book": DocumentType.BOOK,
            "bookchapter": DocumentType.BOOK_CHAPTER,
            "dataset": DocumentType.DATASET,
            "review": DocumentType.REVIEW,
            "preprint": DocumentType.PREPRINT,
        }
        return mapping.get(type_str.replace(" ", ""), DocumentType.OTHER)
