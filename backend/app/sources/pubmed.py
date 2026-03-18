"""PubMed source adapter.

PubMed is a free search engine for biomedical and life sciences literature.
API Documentation: https://www.ncbi.nlm.nih.gov/home/develop/api/
"""

import xml.etree.ElementTree as ET
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


class PubMedAdapter(BaseSourceAdapter):
    """
    PubMed source adapter.

    Provides access to biomedical literature through NCBI's E-utilities API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        email: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize PubMed adapter.

        Args:
            api_key: NCBI API key for higher rate limits
            email: Email for API identification
            timeout: Request timeout
            max_retries: Max retries for failed requests
        """
        super().__init__(timeout, max_retries)
        self._api_key = api_key
        self._email = email

    @property
    def name(self) -> str:
        return "pubmed"

    @property
    def display_name(self) -> str:
        return "PubMed"

    @property
    def base_url(self) -> str:
        return "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

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
            rate_limit_per_second=10.0 if self._api_key else 3.0,
            requires_api_key=False,
        )

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperSearchResult:
        """Search PubMed for papers."""
        # Build search query
        search_terms = [query]

        if filters:
            if filters.year_from:
                search_terms.append(f"{filters.year_from}[PDAT]:{filters.year_to or 3000}[PDAT]")
            if filters.author:
                search_terms.append(f"{filters.author}[Author]")
            if filters.title_contains:
                search_terms.append(f"{filters.title_contains}[Title]")

        full_query = " AND ".join(search_terms)

        # First, search to get PMIDs
        search_params: dict[str, Any] = {
            "db": "pubmed",
            "term": full_query,
            "retstart": (page - 1) * page_size,
            "retmax": min(page_size, self.capabilities.max_results_per_request),
            "retmode": "json",
            "sort": "relevance",
        }

        if self._api_key:
            search_params["api_key"] = self._api_key
        if self._email:
            search_params["email"] = self._email

        try:
            # Search for IDs
            search_data = await self._make_request(
                "GET",
                f"{self.base_url}/esearch.fcgi",
                params=search_params,
            )

            result = search_data.get("esearchresult", {})
            pmids = result.get("idlist", [])
            total = int(result.get("count", 0))

            if not pmids:
                return PaperSearchResult(
                    papers=[],
                    total_results=total,
                    query=query,
                    source=self.name,
                    page=page,
                    page_size=page_size,
                    has_more=False,
                )

            # Fetch details for the PMIDs
            papers = await self._fetch_details(pmids)

            return PaperSearchResult(
                papers=papers,
                total_results=total,
                query=query,
                source=self.name,
                page=page,
                page_size=page_size,
                has_more=page * page_size < total,
            )
        except Exception as e:
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
        """Get a paper by DOI from PubMed."""
        try:
            # Search by DOI
            search_params = {
                "db": "pubmed",
                "term": f"{doi}[DOI]",
                "retmode": "json",
            }
            if self._api_key:
                search_params["api_key"] = self._api_key

            search_data = await self._make_request(
                "GET",
                f"{self.base_url}/esearch.fcgi",
                params=search_params,
            )

            pmids = search_data.get("esearchresult", {}).get("idlist", [])
            if not pmids:
                return None

            papers = await self._fetch_details([pmids[0]])
            return papers[0] if papers else None
        except Exception:
            return None

    async def get_by_id(self, source_id: str) -> Paper | None:
        """Get a paper by PMID."""
        try:
            papers = await self._fetch_details([source_id])
            return papers[0] if papers else None
        except Exception:
            return None

    async def _fetch_details(self, pmids: list[str]) -> list[Paper]:
        """Fetch detailed information for a list of PMIDs."""
        fetch_params: dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
        }

        if self._api_key:
            fetch_params["api_key"] = self._api_key
        if self._email:
            fetch_params["email"] = self._email

        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/efetch.fcgi",
            params=fetch_params,
        )
        response.raise_for_status()

        return self._parse_pubmed_xml(response.text)

    def _parse_pubmed_xml(self, xml_content: str) -> list[Paper]:
        """Parse PubMed XML response."""
        papers = []

        try:
            root = ET.fromstring(xml_content)

            for article in root.findall(".//PubmedArticle"):
                paper = self._parse_article(article)
                if paper:
                    papers.append(paper)

        except ET.ParseError:
            pass

        return papers

    def _parse_article(self, article: ET.Element) -> Paper | None:
        """Parse a single PubMed article."""
        try:
            medline = article.find("MedlineCitation")
            if medline is None:
                return None

            article_data = medline.find("Article")
            if article_data is None:
                return None

            # Extract PMID
            pmid_elem = medline.find("PMID")
            pmid = pmid_elem.text if pmid_elem is not None and pmid_elem.text else ""

            # Extract title
            title_elem = article_data.find("ArticleTitle")
            title = title_elem.text if title_elem is not None and title_elem.text else "Untitled"

            # Extract abstract
            abstract = None
            abstract_elem = article_data.find("Abstract/AbstractText")
            if abstract_elem is not None:
                abstract = abstract_elem.text or ""
                # Handle structured abstracts
                for part in article_data.findall("Abstract/AbstractText"):
                    if part.text:
                        label = part.get("Label", "")
                        if label:
                            abstract += f"\n{label}: {part.text}"
                        else:
                            abstract = part.text

            # Extract authors
            authors = []
            author_list = article_data.find("AuthorList")
            if author_list is not None:
                for author_elem in author_list.findall("Author"):
                    name_parts = []
                    given = author_elem.find("ForeName")
                    family = author_elem.find("LastName")

                    if given is not None and given.text:
                        name_parts.append(given.text)
                    if family is not None and family.text:
                        name_parts.append(family.text)

                    if name_parts:
                        affiliations = []
                        for aff in author_elem.findall("AffiliationInfo/Affiliation"):
                            if aff.text:
                                affiliations.append(aff.text)

                        authors.append(Author(
                            name=" ".join(name_parts),
                            given_name=given.text if given is not None else None,
                            family_name=family.text if family is not None else None,
                            affiliations=affiliations,
                        ))

            # Extract publication date
            pub_date = None
            year = None
            journal_info = article_data.find("Journal/JournalIssue/PubDate")
            if journal_info is not None:
                year_elem = journal_info.find("Year")
                month_elem = journal_info.find("Month")
                day_elem = journal_info.find("Day")

                if year_elem is not None and year_elem.text:
                    year = int(year_elem.text)
                    month = 1
                    day = 1

                    if month_elem is not None and month_elem.text:
                        try:
                            month = int(month_elem.text)
                        except ValueError:
                            # Handle month names
                            month_map = {
                                "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                                "may": 5, "jun": 6, "jul": 7, "aug": 8,
                                "sep": 9, "oct": 10, "nov": 11, "dec": 12,
                            }
                            month = month_map.get(month_elem.text.lower()[:3], 1)

                    if day_elem is not None and day_elem.text:
                        try:
                            day = int(day_elem.text)
                        except ValueError:
                            pass

                    try:
                        pub_date = date(year, month, day)
                    except ValueError:
                        pass

            # Extract journal info
            journal = None
            journal_elem = article_data.find("Journal")
            if journal_elem is not None:
                journal_title = journal_elem.find("Title")
                issn_elem = journal_elem.find("ISSN")
                volume_elem = journal_elem.find("JournalIssue/Volume")
                issue_elem = journal_elem.find("JournalIssue/Issue")

                journal = Journal(
                    name=journal_title.text if journal_title is not None else None,
                    issn=issn_elem.text if issn_elem is not None else None,
                    volume=volume_elem.text if volume_elem is not None else None,
                    issue=issue_elem.text if issue_elem is not None else None,
                )

            # Extract identifiers
            identifiers = [Identifier(type="pmid", value=pmid)]

            # Look for DOI
            doi = None
            article_ids = article.find("PubmedData/ArticleIdList")
            if article_ids is not None:
                for id_elem in article_ids.findall("ArticleId"):
                    id_type = id_elem.get("IdType", "")
                    if id_type == "doi" and id_elem.text:
                        doi = id_elem.text
                        identifiers.append(Identifier(type="doi", value=doi))
                    elif id_type == "pmc" and id_elem.text:
                        identifiers.append(Identifier(type="pmc", value=id_elem.text))

            # Extract MeSH terms
            mesh_terms = []
            mesh_list = medline.find("MeshHeadingList")
            if mesh_list is not None:
                for mesh in mesh_list.findall("MeshHeading/DescriptorName"):
                    if mesh.text:
                        mesh_terms.append(mesh.text)

            # Extract keywords
            keywords = []
            keyword_list = medline.find("KeywordList")
            if keyword_list is not None:
                for kw in keyword_list.findall("Keyword"):
                    if kw.text:
                        keywords.append(kw.text)

            # Build paper
            paper = Paper(
                title=title,
                abstract=abstract,
                authors=authors,
                document_type=DocumentType.JOURNAL_ARTICLE,
                publication_date=pub_date,
                year=year,
                journal=journal,
                doi=doi,
                identifiers=identifiers,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                keywords=keywords,
                mesh_terms=mesh_terms[:20],
                is_open_access=False,  # Would need to check PMC
            )

            # Add source info
            paper.add_source(self._create_source_info(
                source_id=pmid,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            ))

            paper.dedupe_key = paper.generate_dedupe_key()
            return paper

        except Exception:
            return None

    def _normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """Not used for PubMed - we parse XML directly."""
        raise NotImplementedError("PubMed uses XML parsing, not JSON normalization")
