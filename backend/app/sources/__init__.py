"""Academic source adapters.

This module provides adapters for various academic data sources:
- OpenAlex
- Crossref
- Semantic Scholar
- arXiv
- PubMed/Europe PMC

All adapters return normalized Paper objects for consistent handling.
"""

from app.sources.base import BaseSourceAdapter, SourceCapabilities
from app.sources.manager import SourceManager, cleanup_sources, get_source_manager

__all__ = [
    "BaseSourceAdapter",
    "SourceCapabilities",
    "SourceManager",
    "get_source_manager",
    "cleanup_sources",
]
