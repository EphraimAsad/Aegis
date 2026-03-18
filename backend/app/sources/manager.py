"""Source manager for orchestrating searches across multiple academic sources."""

import asyncio
from typing import Any

from app.schemas.paper import (
    AggregatedSearchResult,
    Paper,
    PaperSearchResult,
    SearchFilters,
)
from app.sources.base import BaseSourceAdapter


class SourceManager:
    """
    Manager for academic source adapters.

    Handles registration, search orchestration, and deduplication
    across multiple academic data sources.
    """

    def __init__(self) -> None:
        """Initialize the source manager."""
        self._sources: dict[str, BaseSourceAdapter] = {}

    def register(self, source: BaseSourceAdapter) -> None:
        """
        Register a source adapter.

        Args:
            source: The source adapter to register
        """
        self._sources[source.name] = source

    def unregister(self, name: str) -> None:
        """
        Unregister a source adapter.

        Args:
            name: Source name to unregister
        """
        if name in self._sources:
            del self._sources[name]

    def get(self, name: str) -> BaseSourceAdapter | None:
        """
        Get a source adapter by name.

        Args:
            name: Source name

        Returns:
            Source adapter or None if not found
        """
        return self._sources.get(name)

    def list_sources(self) -> list[str]:
        """
        List all registered source names.

        Returns:
            List of source names
        """
        return list(self._sources.keys())

    def get_source_info(self, name: str) -> dict[str, Any] | None:
        """
        Get information about a source.

        Args:
            name: Source name

        Returns:
            Source information dict or None
        """
        source = self._sources.get(name)
        if not source:
            return None

        return {
            "name": source.name,
            "display_name": source.display_name,
            "capabilities": source.capabilities.model_dump(),
        }

    def list_all_info(self) -> list[dict[str, Any]]:
        """
        Get information about all registered sources.

        Returns:
            List of source information dicts
        """
        return [
            self.get_source_info(name)
            for name in self._sources
            if self.get_source_info(name)
        ]

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        sources: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
        deduplicate: bool = True,
    ) -> AggregatedSearchResult:
        """
        Search across multiple sources and aggregate results.

        Args:
            query: Search query
            filters: Search filters
            sources: List of source names to search (None = all)
            page: Page number
            page_size: Results per page per source
            deduplicate: Whether to deduplicate results

        Returns:
            Aggregated search results
        """
        # Determine which sources to search
        source_names = sources or list(self._sources.keys())
        active_sources = [
            self._sources[name]
            for name in source_names
            if name in self._sources
        ]

        if not active_sources:
            return AggregatedSearchResult(
                papers=[],
                total_from_sources={},
                deduplicated_count=0,
                original_count=0,
                query=query,
                filters=filters,
                sources_searched=[],
                errors={},
            )

        # Search all sources concurrently
        tasks = [
            self._search_source(source, query, filters, page, page_size)
            for source in active_sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_papers: list[Paper] = []
        total_from_sources: dict[str, int] = {}
        errors: dict[str, str] = {}

        for source, result in zip(active_sources, results, strict=False):
            if isinstance(result, Exception):
                errors[source.name] = str(result)
            elif isinstance(result, PaperSearchResult):
                all_papers.extend(result.papers)
                total_from_sources[source.name] = result.total_results

        original_count = len(all_papers)

        # Deduplicate if requested
        if deduplicate:
            all_papers = self._deduplicate(all_papers)

        return AggregatedSearchResult(
            papers=all_papers,
            total_from_sources=total_from_sources,
            deduplicated_count=len(all_papers),
            original_count=original_count,
            query=query,
            filters=filters,
            sources_searched=[s.name for s in active_sources],
            errors=errors,
        )

    async def _search_source(
        self,
        source: BaseSourceAdapter,
        query: str,
        filters: SearchFilters | None,
        page: int,
        page_size: int,
    ) -> PaperSearchResult:
        """Search a single source with error handling."""
        try:
            return await source.search(query, filters, page, page_size)
        except Exception:
            # Return empty result on error
            return PaperSearchResult(
                papers=[],
                total_results=0,
                query=query,
                source=source.name,
                page=page,
                page_size=page_size,
                has_more=False,
            )

    def _deduplicate(self, papers: list[Paper]) -> list[Paper]:
        """
        Deduplicate papers based on DOI or title+year.

        When duplicates are found, merges source information.

        Args:
            papers: List of papers to deduplicate

        Returns:
            Deduplicated list of papers
        """
        seen: dict[str, Paper] = {}

        for paper in papers:
            key = paper.dedupe_key or paper.generate_dedupe_key()

            if key in seen:
                # Merge sources from duplicate
                existing = seen[key]
                for source in paper.sources:
                    if source.name not in [s.name for s in existing.sources]:
                        existing.sources.append(source)

                # Update citation count if higher
                if paper.citation_count and (
                    not existing.citation_count or paper.citation_count > existing.citation_count
                ):
                    existing.citation_count = paper.citation_count

                # Add any missing identifiers
                existing_id_values = {i.value for i in existing.identifiers}
                for identifier in paper.identifiers:
                    if identifier.value not in existing_id_values:
                        existing.identifiers.append(identifier)

            else:
                seen[key] = paper

        return list(seen.values())

    async def get_by_doi(self, doi: str, sources: list[str] | None = None) -> Paper | None:
        """
        Look up a paper by DOI across sources.

        Args:
            doi: The DOI to look up
            sources: Sources to search (None = all)

        Returns:
            Paper if found, None otherwise
        """
        source_names = sources or list(self._sources.keys())

        for name in source_names:
            source = self._sources.get(name)
            if source and source.capabilities.supports_doi_lookup:
                paper = await source.get_by_doi(doi)
                if paper:
                    return paper

        return None

    async def healthcheck_all(self) -> dict[str, bool]:
        """
        Check health of all registered sources.

        Returns:
            Dict of source name to health status
        """
        results = {}
        for name, source in self._sources.items():
            try:
                results[name] = await source.healthcheck()
            except Exception:
                results[name] = False
        return results

    async def close_all(self) -> None:
        """Close all source connections."""
        for source in self._sources.values():
            await source.close()


# Global source manager instance
_source_manager: SourceManager | None = None


def get_source_manager() -> SourceManager:
    """
    Get the global source manager instance.

    Creates and initializes the manager on first call.

    Returns:
        SourceManager: The global source manager
    """
    global _source_manager

    if _source_manager is None:
        _source_manager = SourceManager()
        _initialize_default_sources(_source_manager)

    return _source_manager


def _initialize_default_sources(manager: SourceManager) -> None:
    """
    Initialize default source adapters.

    Args:
        manager: The source manager to initialize
    """
    # Register OpenAlex (no API key required)
    from app.sources.openalex import OpenAlexAdapter
    manager.register(OpenAlexAdapter())

    # Register Crossref (no API key required)
    from app.sources.crossref import CrossrefAdapter
    manager.register(CrossrefAdapter())

    # Register Semantic Scholar (API key optional)
    from app.sources.semantic_scholar import SemanticScholarAdapter
    manager.register(SemanticScholarAdapter())

    # Register arXiv (no API key required)
    from app.sources.arxiv import ArxivAdapter
    manager.register(ArxivAdapter())

    # Register PubMed (API key optional)
    from app.sources.pubmed import PubMedAdapter
    manager.register(PubMedAdapter())


async def cleanup_sources() -> None:
    """Cleanup source connections on shutdown."""
    global _source_manager
    if _source_manager is not None:
        await _source_manager.close_all()
        _source_manager = None
