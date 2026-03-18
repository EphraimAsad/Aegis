"""Tagging and categorization service.

Provides auto-tagging of documents based on content analysis
and predefined taxonomies.
"""

import json
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.providers import get_provider_manager
from app.providers.base import BaseProvider


class TagSource(StrEnum):
    """Source of tags."""

    MANUAL = "manual"
    AUTO_KEYWORDS = "auto_keywords"
    AUTO_AI = "auto_ai"
    MESH = "mesh"
    SUBJECT = "subject"


@dataclass
class TagSuggestion:
    """A suggested tag with confidence."""

    tag: str
    confidence: float
    source: TagSource
    category: str | None = None


# Predefined research categories
RESEARCH_CATEGORIES = {
    "methodology": [
        "experimental",
        "theoretical",
        "computational",
        "qualitative",
        "quantitative",
        "mixed-methods",
        "meta-analysis",
        "review",
        "case-study",
        "survey",
        "longitudinal",
        "cross-sectional",
    ],
    "domain": [
        "biomedical",
        "clinical",
        "engineering",
        "physics",
        "chemistry",
        "biology",
        "computer-science",
        "mathematics",
        "social-science",
        "economics",
        "psychology",
        "environmental",
        "materials",
    ],
    "impact": [
        "high-citation",
        "breakthrough",
        "foundational",
        "incremental",
        "replication",
        "negative-results",
    ],
    "access": [
        "open-access",
        "preprint",
        "peer-reviewed",
        "retracted",
    ],
}

# Prompt templates
AUTO_TAG_PROMPT = """Analyze the following academic paper and suggest relevant tags. Consider:
- Research methodology
- Subject domain
- Key concepts and techniques
- Target application areas

Title: {title}

Abstract: {abstract}

Keywords from paper: {keywords}
Subjects: {subjects}

Return a JSON array of tag suggestions:
[
  {{"tag": "tag-name", "confidence": 0.0-1.0, "category": "methodology|domain|concept|application"}}
]

Provide 5-10 relevant tags. Tags should be lowercase with hyphens. Return only valid JSON."""

CATEGORIZE_PROMPT = """Categorize the following academic paper into the most relevant research categories.

Title: {title}
Abstract: {abstract}

Available categories:
- Methodology: {methodology_cats}
- Domain: {domain_cats}
- Impact: {impact_cats}

Return a JSON object with the best-matching categories:
{{
  "methodology": ["selected-category", ...],
  "domain": ["selected-category", ...],
  "primary_domain": "single-best-domain"
}}

Return only valid JSON."""


class TaggingService:
    """Service for document tagging and categorization."""

    def __init__(
        self,
        db: AsyncSession,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """
        Initialize tagging service.

        Args:
            db: Database session
            provider_name: Provider to use (None = default)
            model_name: Model to use (None = provider default)
        """
        self.db = db
        self._provider_name = provider_name
        self._model_name = model_name
        self._provider: BaseProvider | None = None

    async def _get_provider(self) -> BaseProvider:
        """Get or initialize the provider."""
        if self._provider is None:
            manager = get_provider_manager()
            if self._provider_name:
                self._provider = manager.get(self._provider_name)
            else:
                self._provider = manager.get_default()

            if not self._provider:
                raise RuntimeError("No tagging provider available")

        return self._provider

    def extract_keyword_tags(self, document: Document) -> list[TagSuggestion]:
        """
        Extract tags from document keywords and subjects.

        Args:
            document: Document to tag

        Returns:
            List of tag suggestions
        """
        suggestions = []

        # Convert keywords to tags
        if document.keywords:
            for keyword in document.keywords:
                tag = self._normalize_tag(keyword)
                if tag:
                    suggestions.append(
                        TagSuggestion(
                            tag=tag,
                            confidence=0.9,
                            source=TagSource.AUTO_KEYWORDS,
                        )
                    )

        # Convert subjects to tags
        if document.subjects:
            for subject in document.subjects:
                tag = self._normalize_tag(subject)
                if tag:
                    suggestions.append(
                        TagSuggestion(
                            tag=tag,
                            confidence=0.85,
                            source=TagSource.SUBJECT,
                        )
                    )

        # Convert MeSH terms to tags
        if document.mesh_terms:
            for mesh in document.mesh_terms:
                tag = self._normalize_tag(mesh)
                if tag:
                    suggestions.append(
                        TagSuggestion(
                            tag=tag,
                            confidence=0.95,
                            source=TagSource.MESH,
                            category="biomedical",
                        )
                    )

        return suggestions

    def _normalize_tag(self, text: str) -> str | None:
        """Normalize a tag string."""
        if not text:
            return None

        # Convert to lowercase, replace spaces with hyphens
        tag = text.lower().strip()
        tag = tag.replace(" ", "-")
        tag = tag.replace("_", "-")

        # Remove special characters except hyphens
        tag = "".join(c for c in tag if c.isalnum() or c == "-")

        # Clean up multiple hyphens
        while "--" in tag:
            tag = tag.replace("--", "-")

        # Remove leading/trailing hyphens
        tag = tag.strip("-")

        # Limit length
        if len(tag) < 2 or len(tag) > 50:
            return None

        return tag

    async def generate_ai_tags(
        self,
        document: Document,
        max_tags: int = 10,
    ) -> list[TagSuggestion]:
        """
        Generate tags using AI analysis.

        Args:
            document: Document to tag
            max_tags: Maximum number of tags to suggest

        Returns:
            List of AI-generated tag suggestions
        """
        provider = await self._get_provider()

        prompt = AUTO_TAG_PROMPT.format(
            title=document.title,
            abstract=document.abstract or "No abstract available",
            keywords=", ".join(document.keywords or []) or "None",
            subjects=", ".join(document.subjects or []) or "None",
        )

        response = await provider.complete(
            prompt=prompt,
            model=self._model_name,
        )

        # Parse response
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            tags_data = json.loads(content)
            if not isinstance(tags_data, list):
                tags_data = [tags_data]

            suggestions = []
            for item in tags_data[:max_tags]:
                tag = self._normalize_tag(item.get("tag", ""))
                if tag:
                    suggestions.append(
                        TagSuggestion(
                            tag=tag,
                            confidence=float(item.get("confidence", 0.7)),
                            source=TagSource.AUTO_AI,
                            category=item.get("category"),
                        )
                    )

            return suggestions

        except (json.JSONDecodeError, ValueError):
            return []

    async def categorize_document(
        self,
        document: Document,
    ) -> dict:
        """
        Categorize a document into predefined research categories.

        Args:
            document: Document to categorize

        Returns:
            Dict with methodology, domain, and primary_domain
        """
        provider = await self._get_provider()

        prompt = CATEGORIZE_PROMPT.format(
            title=document.title,
            abstract=document.abstract or "No abstract available",
            methodology_cats=", ".join(RESEARCH_CATEGORIES["methodology"]),
            domain_cats=", ".join(RESEARCH_CATEGORIES["domain"]),
            impact_cats=", ".join(RESEARCH_CATEGORIES["impact"]),
        )

        response = await provider.complete(
            prompt=prompt,
            model=self._model_name,
        )

        # Parse response
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            categories = json.loads(content)
            return {
                "methodology": categories.get("methodology", []),
                "domain": categories.get("domain", []),
                "primary_domain": categories.get("primary_domain"),
            }

        except (json.JSONDecodeError, ValueError):
            return {
                "methodology": [],
                "domain": [],
                "primary_domain": None,
            }

    async def auto_tag_document(
        self,
        document_id: int,
        use_ai: bool = True,
        min_confidence: float = 0.5,
    ) -> list[str]:
        """
        Automatically tag a document.

        Args:
            document_id: Document ID
            use_ai: Whether to use AI for additional tags
            min_confidence: Minimum confidence threshold

        Returns:
            List of applied tags
        """
        from app.services.document import DocumentService

        doc_service = DocumentService(self.db)
        document = await doc_service.get(document_id)

        all_suggestions: list[TagSuggestion] = []

        # Get keyword-based tags
        keyword_tags = self.extract_keyword_tags(document)
        all_suggestions.extend(keyword_tags)

        # Get AI-generated tags
        if use_ai:
            ai_tags = await self.generate_ai_tags(document)
            all_suggestions.extend(ai_tags)

        # Deduplicate and filter by confidence
        seen_tags = set()
        final_tags = []

        for suggestion in sorted(
            all_suggestions, key=lambda x: x.confidence, reverse=True
        ):
            if (
                suggestion.tag not in seen_tags
                and suggestion.confidence >= min_confidence
            ):
                seen_tags.add(suggestion.tag)
                final_tags.append(suggestion.tag)

        # Update document tags
        existing_tags = set(document.tags or [])
        new_tags = list(existing_tags.union(final_tags))

        await doc_service.update(document_id, type("Request", (), {"tags": new_tags})())
        await self.db.commit()

        return new_tags

    async def suggest_tags_for_project(
        self,
        project_id: int,
        min_occurrence: int = 2,
    ) -> list[dict]:
        """
        Suggest common tags across a project's documents.

        Args:
            project_id: Project ID
            min_occurrence: Minimum occurrences for a tag

        Returns:
            List of tag suggestions with counts
        """
        from app.services.document import DocumentService

        doc_service = DocumentService(self.db)
        documents, _ = await doc_service.list(project_id, page_size=1000)

        # Count tag occurrences
        tag_counts: dict[str, int] = {}
        for doc in documents:
            for tag in doc.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Filter and sort
        suggestions = [
            {"tag": tag, "count": count, "percentage": count / len(documents) * 100}
            for tag, count in tag_counts.items()
            if count >= min_occurrence
        ]

        suggestions.sort(key=lambda x: x["count"], reverse=True)

        return suggestions

    def get_available_categories(self) -> dict:
        """Get all available predefined categories."""
        return RESEARCH_CATEGORIES.copy()


def get_tagging_service(
    db: AsyncSession,
    provider_name: str | None = None,
    model_name: str | None = None,
) -> TaggingService:
    """
    Get a tagging service instance.

    Args:
        db: Database session
        provider_name: Provider name (None = default)
        model_name: Model name (None = provider default)

    Returns:
        TaggingService instance
    """
    return TaggingService(
        db=db,
        provider_name=provider_name,
        model_name=model_name,
    )
