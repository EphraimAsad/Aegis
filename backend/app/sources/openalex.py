"""OpenAlex source adapter.

OpenAlex is a free, open catalog of the world's scholarly works.
API Documentation: https://docs.openalex.org/
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


class OpenAlexAdapter(BaseSourceAdapter):
    """
    OpenAlex source adapter.

    OpenAlex provides free access to scholarly metadata including
    papers, authors, institutions, and concepts.
    """

    def __init__(
        self,
        email: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize OpenAlex adapter.

        Args:
            email: Email for polite pool (faster rate limits)
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
        return "openalex"

    @property
    def display_name(self) -> str:
        return "OpenAlex"

    @property
    def base_url(self) -> str:
        return "https://api.openalex.org"

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
            max_results_per_request=200,
            rate_limit_per_second=10.0,
            requires_api_key=False,
        )

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperSearchResult:
        """Search OpenAlex for papers."""
        params: dict[str, Any] = {
            "search": query,
            "page": page,
            "per_page": min(page_size, self.capabilities.max_results_per_request),
        }

        # Build filter string
        filter_parts = []

        if filters:
            if filters.year_from:
                filter_parts.append(f"publication_year:>{filters.year_from - 1}")
            if filters.year_to:
                filter_parts.append(f"publication_year:<{filters.year_to + 1}")
            if filters.open_access_only:
                filter_parts.append("is_oa:true")
            if filters.min_citations > 0:
                filter_parts.append(f"cited_by_count:>{filters.min_citations - 1}")
            if filters.document_types:
                types = [self._map_document_type(t) for t in filters.document_types]
                filter_parts.append(f"type:{'|'.join(types)}")

        if filter_parts:
            params["filter"] = ",".join(filter_parts)

        # Add email for polite pool
        if self._email:
            params["mailto"] = self._email

        try:
            data = await self._make_request(
                "GET", f"{self.base_url}/works", params=params
            )

            papers = [self._normalize_paper(work) for work in data.get("results", [])]
            total = data.get("meta", {}).get("count", 0)

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
        """Get a paper by DOI from OpenAlex."""
        try:
            # OpenAlex accepts DOI in the URL
            url = f"{self.base_url}/works/https://doi.org/{doi}"
            if self._email:
                url += f"?mailto={self._email}"

            data = await self._make_request("GET", url)
            return self._normalize_paper(data)
        except Exception:
            return None

    async def get_by_id(self, source_id: str) -> Paper | None:
        """Get a paper by OpenAlex ID."""
        try:
            url = f"{self.base_url}/works/{source_id}"
            if self._email:
                url += f"?mailto={self._email}"

            data = await self._make_request("GET", url)
            return self._normalize_paper(data)
        except Exception:
            return None

    def _normalize_paper(self, raw: dict[str, Any]) -> Paper:
        """Convert OpenAlex work to normalized Paper."""
        # Extract authors
        authors = []
        for authorship in raw.get("authorships", []):
            author_data = authorship.get("author", {})
            affiliations = [
                inst.get("display_name", "")
                for inst in authorship.get("institutions", [])
                if inst.get("display_name")
            ]
            authors.append(
                Author(
                    name=author_data.get("display_name", "Unknown"),
                    orcid=author_data.get("orcid"),
                    affiliations=affiliations,
                )
            )

        # Extract publication date
        pub_date = None
        year = raw.get("publication_year")
        if raw.get("publication_date"):
            try:
                pub_date = date.fromisoformat(raw["publication_date"])
            except ValueError:
                pass

        # Extract journal info
        journal = None
        primary_location = raw.get("primary_location", {})
        source = primary_location.get("source", {})
        if source:
            journal = Journal(
                name=source.get("display_name"),
                issn=source.get("issn_l"),
                publisher=source.get("host_organization_name"),
            )

        # Build identifiers
        identifiers = []
        if raw.get("doi"):
            identifiers.append(
                Identifier(type="doi", value=raw["doi"].replace("https://doi.org/", ""))
            )
        if raw.get("ids", {}).get("pmid"):
            identifiers.append(Identifier(type="pmid", value=raw["ids"]["pmid"]))

        # Determine document type
        doc_type = self._parse_document_type(raw.get("type", ""))

        # Extract concepts as subjects
        subjects = [
            concept.get("display_name")
            for concept in raw.get("concepts", [])[:10]
            if concept.get("display_name")
        ]

        # Extract keywords from topics
        keywords = [
            topic.get("display_name")
            for topic in raw.get("topics", [])[:10]
            if topic.get("display_name")
        ]

        # Build paper
        paper = Paper(
            title=raw.get("title", "Untitled"),
            abstract=self._extract_abstract(raw),
            authors=authors,
            document_type=doc_type,
            publication_date=pub_date,
            year=year,
            journal=journal,
            language=raw.get("language"),
            doi=(
                raw.get("doi", "").replace("https://doi.org/", "")
                if raw.get("doi")
                else None
            ),
            identifiers=identifiers,
            url=raw.get("id"),
            pdf_url=primary_location.get("pdf_url"),
            open_access_url=raw.get("open_access", {}).get("oa_url"),
            citation_count=raw.get("cited_by_count"),
            reference_count=raw.get("referenced_works_count"),
            keywords=keywords,
            subjects=subjects,
            is_open_access=raw.get("open_access", {}).get("is_oa", False),
            is_preprint=doc_type == DocumentType.PREPRINT,
            is_retracted=raw.get("is_retracted", False),
        )

        # Add source info
        paper.add_source(
            self._create_source_info(
                source_id=raw.get("id", "").replace("https://openalex.org/", ""),
                url=raw.get("id"),
            )
        )

        paper.dedupe_key = paper.generate_dedupe_key()
        return paper

    def _extract_abstract(self, raw: dict[str, Any]) -> str | None:
        """Extract abstract from OpenAlex inverted index format."""
        abstract_index = raw.get("abstract_inverted_index")
        if not abstract_index:
            return None

        # Reconstruct abstract from inverted index
        positions: list[tuple[int, str]] = []
        for word, indices in abstract_index.items():
            for idx in indices:
                positions.append((idx, word))

        positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in positions)

    def _parse_document_type(self, type_str: str) -> DocumentType:
        """Parse OpenAlex type to DocumentType enum."""
        mapping = {
            "article": DocumentType.JOURNAL_ARTICLE,
            "journal-article": DocumentType.JOURNAL_ARTICLE,
            "book": DocumentType.BOOK,
            "book-chapter": DocumentType.BOOK_CHAPTER,
            "dissertation": DocumentType.DISSERTATION,
            "dataset": DocumentType.DATASET,
            "preprint": DocumentType.PREPRINT,
            "review": DocumentType.REVIEW,
            "proceedings-article": DocumentType.CONFERENCE_PAPER,
        }
        return mapping.get(type_str.lower(), DocumentType.OTHER)

    def _map_document_type(self, doc_type: DocumentType) -> str:
        """Map DocumentType enum to OpenAlex type string."""
        mapping = {
            DocumentType.JOURNAL_ARTICLE: "article",
            DocumentType.BOOK: "book",
            DocumentType.BOOK_CHAPTER: "book-chapter",
            DocumentType.DISSERTATION: "dissertation",
            DocumentType.PREPRINT: "preprint",
            DocumentType.CONFERENCE_PAPER: "proceedings-article",
        }
        return mapping.get(doc_type, "article")
