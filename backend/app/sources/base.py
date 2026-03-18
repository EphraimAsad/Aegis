"""Base adapter interface for academic sources."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel

from app.schemas.paper import Paper, PaperSearchResult, SearchFilters, SourceInfo


class SourceCapabilities(BaseModel):
    """Describes what a source adapter supports."""

    supports_fulltext_search: bool = True
    supports_title_search: bool = True
    supports_author_search: bool = True
    supports_doi_lookup: bool = True
    supports_date_filter: bool = True
    supports_citation_filter: bool = False
    supports_open_access_filter: bool = False
    supports_pagination: bool = True
    max_results_per_request: int = 100
    rate_limit_per_second: float = 10.0
    requires_api_key: bool = False


class BaseSourceAdapter(ABC):
    """
    Abstract base class for academic source adapters.

    All source adapters (OpenAlex, Crossref, etc.) must implement this interface.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the adapter.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers=self._get_headers(),
            )
        return self._client

    def _get_headers(self) -> dict[str, str]:
        """Get default headers for requests. Override in subclasses."""
        return {
            "User-Agent": "Aegis/0.1.0 (Academic Research Tool; mailto:contact@example.com)",
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Source name identifier.

        Returns:
            str: Unique source name (e.g., "openalex", "crossref")
        """
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable source name.

        Returns:
            str: Display name (e.g., "OpenAlex", "Crossref")
        """
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """
        Base URL for the API.

        Returns:
            str: API base URL
        """
        pass

    @property
    @abstractmethod
    def capabilities(self) -> SourceCapabilities:
        """
        Get source capabilities.

        Returns:
            SourceCapabilities: What this source supports
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperSearchResult:
        """
        Search for papers.

        Args:
            query: Search query string
            filters: Optional search filters
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            PaperSearchResult: Search results with papers
        """
        pass

    @abstractmethod
    async def get_by_doi(self, doi: str) -> Paper | None:
        """
        Get a paper by its DOI.

        Args:
            doi: The DOI to look up

        Returns:
            Paper if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_id(self, source_id: str) -> Paper | None:
        """
        Get a paper by its source-specific ID.

        Args:
            source_id: The ID in this source's system

        Returns:
            Paper if found, None otherwise
        """
        pass

    @abstractmethod
    def _normalize_paper(self, raw_data: dict[str, Any]) -> Paper:
        """
        Convert source-specific data to normalized Paper format.

        Args:
            raw_data: Raw data from the source API

        Returns:
            Paper: Normalized paper object
        """
        pass

    async def healthcheck(self) -> bool:
        """
        Check if the source is available.

        Returns:
            bool: True if healthy
        """
        try:
            client = await self._get_client()
            response = await client.get(self.base_url)
            return response.status_code < 500
        except Exception:
            return False

    def _create_source_info(self, source_id: str, url: str | None = None) -> SourceInfo:
        """Create a SourceInfo object for this adapter."""
        return SourceInfo(
            name=self.name,
            id=source_id,
            url=url,
            retrieved_at=datetime.utcnow(),
        )

    async def _make_request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict[str, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            params: Query parameters
            json_data: JSON body

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPError: If request fails after retries
        """
        client = await self._get_client()
        last_error = None

        for attempt in range(self._max_retries):
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:  # Rate limited
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                elif e.response.status_code >= 500:
                    import asyncio
                    await asyncio.sleep(1)
                else:
                    raise
            except httpx.RequestError as e:
                last_error = e
                import asyncio
                await asyncio.sleep(1)

        raise last_error or Exception("Request failed after retries")
