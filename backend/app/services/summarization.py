"""Summarization service.

Uses provider abstraction to generate summaries of documents
at different levels of detail.
"""

import json
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.providers import get_provider_manager
from app.providers.base import BaseProvider


class SummaryLevel(str, Enum):
    """Level of detail for summaries."""

    BRIEF = "brief"  # 1-2 sentences
    STANDARD = "standard"  # 3-5 sentences
    DETAILED = "detailed"  # Full paragraph


@dataclass
class SummaryResult:
    """Result of summary generation."""

    summary: str
    level: SummaryLevel
    model: str
    tokens_used: int


# Prompt templates for different summary types
SUMMARY_PROMPTS = {
    SummaryLevel.BRIEF: """Summarize the following academic paper in 1-2 sentences, focusing on the main contribution:

Title: {title}

Abstract: {abstract}

{full_text_section}

Provide only the summary, no preamble.""",

    SummaryLevel.STANDARD: """Summarize the following academic paper in 3-5 sentences, covering the main objective, methods, and key findings:

Title: {title}

Abstract: {abstract}

{full_text_section}

Provide only the summary, no preamble.""",

    SummaryLevel.DETAILED: """Provide a detailed summary of the following academic paper in one paragraph. Include:
- The research problem being addressed
- The methodology or approach used
- The main findings or contributions
- The implications or significance of the work

Title: {title}

Abstract: {abstract}

{full_text_section}

Provide only the summary, no preamble.""",
}

KEY_FINDINGS_PROMPT = """Extract the key findings from this academic paper. Return as a JSON array of objects with the following structure:
[
  {{
    "finding": "Brief statement of the finding",
    "evidence": "Supporting evidence or data",
    "significance": "Why this finding matters"
  }}
]

Title: {title}

Abstract: {abstract}

{full_text_section}

Return only valid JSON, no other text."""

EVIDENCE_EXTRACTION_PROMPT = """Extract claims and their supporting evidence from this academic paper. Return as a JSON array of objects:
[
  {{
    "claim": "The claim being made",
    "evidence": "The evidence supporting this claim",
    "confidence": 0.0-1.0 (your confidence in the claim being well-supported),
    "location": "Where in the paper this appears (e.g., Abstract, Results, Discussion)"
  }}
]

Title: {title}

Abstract: {abstract}

{full_text_section}

Focus on empirical claims backed by data or citations. Return only valid JSON, no other text."""


class SummarizationService:
    """Service for generating document summaries."""

    def __init__(
        self,
        db: AsyncSession,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """
        Initialize summarization service.

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
                raise RuntimeError("No summarization provider available")

        return self._provider

    def _format_document_context(
        self,
        title: str,
        abstract: str | None,
        full_text: str | None,
        max_full_text_chars: int = 15000,
    ) -> tuple[str, str, str]:
        """Format document content for prompts."""
        abstract_text = abstract or "No abstract available."

        if full_text and len(full_text) > max_full_text_chars:
            full_text = full_text[:max_full_text_chars] + "..."

        full_text_section = ""
        if full_text:
            full_text_section = f"Full Text (excerpt):\n{full_text}"

        return title, abstract_text, full_text_section

    async def summarize(
        self,
        document: Document,
        level: SummaryLevel = SummaryLevel.STANDARD,
    ) -> SummaryResult:
        """
        Generate a summary for a document.

        Args:
            document: Document to summarize
            level: Level of detail for summary

        Returns:
            SummaryResult with the generated summary
        """
        provider = await self._get_provider()

        title, abstract, full_text_section = self._format_document_context(
            document.title,
            document.abstract,
            document.full_text,
        )

        prompt = SUMMARY_PROMPTS[level].format(
            title=title,
            abstract=abstract,
            full_text_section=full_text_section,
        )

        response = await provider.complete(
            prompt=prompt,
            model=self._model_name,
        )

        return SummaryResult(
            summary=response.content.strip(),
            level=level,
            model=response.model,
            tokens_used=response.usage.total_tokens,
        )

    async def extract_key_findings(
        self,
        document: Document,
    ) -> list[dict]:
        """
        Extract key findings from a document.

        Args:
            document: Document to analyze

        Returns:
            List of finding objects
        """
        provider = await self._get_provider()

        title, abstract, full_text_section = self._format_document_context(
            document.title,
            document.abstract,
            document.full_text,
        )

        prompt = KEY_FINDINGS_PROMPT.format(
            title=title,
            abstract=abstract,
            full_text_section=full_text_section,
        )

        response = await provider.complete(
            prompt=prompt,
            model=self._model_name,
        )

        # Parse JSON response
        try:
            content = response.content.strip()
            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            findings = json.loads(content)
            if not isinstance(findings, list):
                findings = [findings]
            return findings
        except json.JSONDecodeError:
            # If parsing fails, return empty list
            return []

    async def extract_evidence_claims(
        self,
        document: Document,
    ) -> list[dict]:
        """
        Extract evidence-backed claims from a document.

        Args:
            document: Document to analyze

        Returns:
            List of claim objects with evidence
        """
        provider = await self._get_provider()

        title, abstract, full_text_section = self._format_document_context(
            document.title,
            document.abstract,
            document.full_text,
        )

        prompt = EVIDENCE_EXTRACTION_PROMPT.format(
            title=title,
            abstract=abstract,
            full_text_section=full_text_section,
        )

        response = await provider.complete(
            prompt=prompt,
            model=self._model_name,
        )

        # Parse JSON response
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            claims = json.loads(content)
            if not isinstance(claims, list):
                claims = [claims]
            return claims
        except json.JSONDecodeError:
            return []

    async def process_document(
        self,
        document_id: int,
        summary_level: SummaryLevel = SummaryLevel.STANDARD,
        extract_findings: bool = True,
        extract_evidence: bool = True,
    ) -> dict:
        """
        Process a document for summarization and extraction.

        Args:
            document_id: Document ID
            summary_level: Level of detail for summary
            extract_findings: Whether to extract key findings
            extract_evidence: Whether to extract evidence claims

        Returns:
            Processing result
        """
        from app.services.document import DocumentService

        doc_service = DocumentService(self.db)
        document = await doc_service.get(document_id)

        result = {
            "document_id": document_id,
            "title": document.title,
        }

        # Generate summary
        summary_result = await self.summarize(document, summary_level)
        await doc_service.set_summary(document_id, summary_result.summary)
        result["summary"] = summary_result.summary
        result["summary_model"] = summary_result.model

        # Extract key findings
        if extract_findings:
            findings = await self.extract_key_findings(document)
            await doc_service.set_key_findings(document_id, findings)
            result["key_findings"] = findings
            result["findings_count"] = len(findings)

        # Extract evidence claims
        if extract_evidence:
            claims = await self.extract_evidence_claims(document)
            await doc_service.set_evidence_claims(document_id, claims)
            result["evidence_claims"] = claims
            result["claims_count"] = len(claims)

        await self.db.commit()

        return result

    async def generate_comparative_summary(
        self,
        documents: list[Document],
    ) -> str:
        """
        Generate a comparative summary across multiple documents.

        Args:
            documents: List of documents to compare

        Returns:
            Comparative summary text
        """
        provider = await self._get_provider()

        # Build context from all documents
        doc_contexts = []
        for doc in documents[:10]:  # Limit to 10 documents
            doc_contexts.append(f"Document: {doc.title}\nAbstract: {doc.abstract or 'N/A'}")

        all_docs = "\n\n---\n\n".join(doc_contexts)

        prompt = f"""Compare and synthesize the following {len(documents)} academic papers. Identify:
1. Common themes and findings
2. Key differences in approaches or conclusions
3. Overall trends in the literature
4. Gaps or areas needing further research

Documents:
{all_docs}

Provide a cohesive comparative analysis in 2-3 paragraphs."""

        response = await provider.complete(
            prompt=prompt,
            model=self._model_name,
        )

        return response.content.strip()


def get_summarization_service(
    db: AsyncSession,
    provider_name: str | None = None,
    model_name: str | None = None,
) -> SummarizationService:
    """
    Get a summarization service instance.

    Args:
        db: Database session
        provider_name: Provider name (None = default)
        model_name: Model name (None = provider default)

    Returns:
        SummarizationService instance
    """
    return SummarizationService(
        db=db,
        provider_name=provider_name,
        model_name=model_name,
    )
