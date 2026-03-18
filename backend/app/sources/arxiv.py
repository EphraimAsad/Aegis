"""arXiv source adapter.

arXiv is a free distribution service and open-access archive for scholarly articles.
API Documentation: https://info.arxiv.org/help/api/index.html
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from app.schemas.paper import (
    Author,
    DocumentType,
    Identifier,
    Paper,
    PaperSearchResult,
    SearchFilters,
)
from app.sources.base import BaseSourceAdapter, SourceCapabilities


class ArxivAdapter(BaseSourceAdapter):
    """
    arXiv source adapter.

    Provides access to preprints and papers from arXiv.org,
    covering physics, mathematics, computer science, and more.
    """

    # arXiv category to subject mapping
    CATEGORY_SUBJECTS = {
        "cs": "Computer Science",
        "math": "Mathematics",
        "physics": "Physics",
        "q-bio": "Quantitative Biology",
        "q-fin": "Quantitative Finance",
        "stat": "Statistics",
        "eess": "Electrical Engineering",
        "econ": "Economics",
        "astro-ph": "Astrophysics",
        "cond-mat": "Condensed Matter",
        "gr-qc": "General Relativity",
        "hep": "High Energy Physics",
        "nlin": "Nonlinear Sciences",
        "nucl": "Nuclear",
        "quant-ph": "Quantum Physics",
    }

    @property
    def name(self) -> str:
        return "arxiv"

    @property
    def display_name(self) -> str:
        return "arXiv"

    @property
    def base_url(self) -> str:
        return "http://export.arxiv.org/api"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_fulltext_search=True,
            supports_title_search=True,
            supports_author_search=True,
            supports_doi_lookup=False,  # arXiv uses its own IDs
            supports_date_filter=True,
            supports_citation_filter=False,
            supports_open_access_filter=False,  # All arXiv is open access
            supports_pagination=True,
            max_results_per_request=100,
            rate_limit_per_second=1.0,  # arXiv has strict rate limits
            requires_api_key=False,
        )

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperSearchResult:
        """Search arXiv for papers."""
        # Build query
        search_query = f"all:{query}"

        if filters:
            if filters.title_contains:
                search_query = f"ti:{filters.title_contains} AND {search_query}"
            if filters.author:
                search_query = f"au:{filters.author} AND {search_query}"

        params = {
            "search_query": search_query,
            "start": (page - 1) * page_size,
            "max_results": min(page_size, self.capabilities.max_results_per_request),
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/query", params=params)
            response.raise_for_status()

            papers, total = self._parse_atom_feed(response.text, filters)

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
        """arXiv doesn't support DOI lookup directly."""
        return None

    async def get_by_id(self, source_id: str) -> Paper | None:
        """Get a paper by arXiv ID."""
        try:
            # Clean the ID
            arxiv_id = source_id.replace("arXiv:", "").replace("arxiv:", "")

            params = {"id_list": arxiv_id}
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/query", params=params)
            response.raise_for_status()

            papers, _ = self._parse_atom_feed(response.text)
            return papers[0] if papers else None
        except Exception:
            return None

    def _parse_atom_feed(
        self,
        xml_content: str,
        filters: SearchFilters | None = None,
    ) -> tuple[list[Paper], int]:
        """Parse arXiv Atom feed response."""
        # Define namespaces
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
        }

        root = ET.fromstring(xml_content)

        # Get total results
        total_elem = root.find("opensearch:totalResults", namespaces)
        total = int(total_elem.text) if total_elem is not None and total_elem.text else 0

        papers = []
        for entry in root.findall("atom:entry", namespaces):
            paper = self._parse_entry(entry, namespaces)
            if paper:
                # Apply date filters if needed
                if filters and paper.year:
                    if filters.year_from and paper.year < filters.year_from:
                        continue
                    if filters.year_to and paper.year > filters.year_to:
                        continue
                papers.append(paper)

        return papers, total

    def _parse_entry(self, entry: ET.Element, ns: dict) -> Paper | None:
        """Parse a single arXiv entry."""
        try:
            # Extract basic info
            title = entry.find("atom:title", ns)
            title_text = title.text.strip().replace("\n", " ") if title is not None and title.text else "Untitled"

            summary = entry.find("atom:summary", ns)
            abstract = summary.text.strip() if summary is not None and summary.text else None

            # Extract arXiv ID from the id URL
            id_elem = entry.find("atom:id", ns)
            arxiv_url = id_elem.text if id_elem is not None and id_elem.text else ""
            arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

            # Extract authors
            authors = []
            for author_elem in entry.findall("atom:author", ns):
                name_elem = author_elem.find("atom:name", ns)
                if name_elem is not None and name_elem.text:
                    affiliations = []
                    for aff in author_elem.findall("arxiv:affiliation", ns):
                        if aff.text:
                            affiliations.append(aff.text)
                    authors.append(Author(
                        name=name_elem.text,
                        affiliations=affiliations,
                    ))

            # Extract dates
            published = entry.find("atom:published", ns)
            pub_date = None
            year = None
            if published is not None and published.text:
                try:
                    dt = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
                    pub_date = dt.date()
                    year = dt.year
                except ValueError:
                    pass

            # Extract categories as subjects
            subjects = []
            primary_category = entry.find("arxiv:primary_category", ns)
            if primary_category is not None:
                cat = primary_category.get("term", "")
                subjects.append(cat)
                # Add human-readable subject
                main_cat = cat.split(".")[0] if "." in cat else cat
                if main_cat in self.CATEGORY_SUBJECTS:
                    subjects.append(self.CATEGORY_SUBJECTS[main_cat])

            for cat_elem in entry.findall("atom:category", ns):
                cat = cat_elem.get("term", "")
                if cat and cat not in subjects:
                    subjects.append(cat)

            # Extract links
            pdf_url = None
            abs_url = None
            for link in entry.findall("atom:link", ns):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href")
                elif link.get("type") == "text/html":
                    abs_url = link.get("href")

            # Extract DOI if present
            doi = None
            doi_elem = entry.find("arxiv:doi", ns)
            if doi_elem is not None and doi_elem.text:
                doi = doi_elem.text

            # Build identifiers
            identifiers = [Identifier(type="arxiv", value=arxiv_id)]
            if doi:
                identifiers.append(Identifier(type="doi", value=doi))

            # Build paper
            paper = Paper(
                title=title_text,
                abstract=abstract,
                authors=authors,
                document_type=DocumentType.PREPRINT,
                publication_date=pub_date,
                year=year,
                doi=doi,
                identifiers=identifiers,
                url=abs_url or arxiv_url,
                pdf_url=pdf_url,
                open_access_url=pdf_url,
                subjects=subjects[:10],  # Limit subjects
                is_open_access=True,  # arXiv is always open access
                is_preprint=True,
            )

            # Add source info
            paper.add_source(self._create_source_info(
                source_id=arxiv_id,
                url=abs_url or arxiv_url,
            ))

            paper.dedupe_key = paper.generate_dedupe_key()
            return paper

        except Exception:
            return None

    def _normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """Not used for arXiv - we parse XML directly."""
        raise NotImplementedError("arXiv uses XML parsing, not JSON normalization")
