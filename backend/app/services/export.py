"""Service for exporting documents in various formats."""

import csv
import io
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus
from app.schemas.export import (
    EXPORT_CONTENT_TYPES,
    EXPORT_EXTENSIONS,
    ExportFormat,
    ExportOptions,
    ExportResponse,
)


class ExportService:
    """Service for exporting documents in various formats."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def export_documents(
        self,
        project_id: int,
        format: ExportFormat,
        options: ExportOptions,
        document_ids: list[int] | None = None,
        filename: str | None = None,
    ) -> ExportResponse:
        """
        Export documents in the specified format.

        Args:
            project_id: Project ID
            format: Export format
            options: Export options
            document_ids: Specific document IDs (None = all)
            filename: Custom filename

        Returns:
            ExportResponse with content
        """
        documents = await self._get_documents(project_id, document_ids)

        # Validate we have documents to export
        if not documents:
            raise ValueError(
                "No documents to export. Run a research job first to collect papers."
            )

        # Generate content based on format
        if format == ExportFormat.CSV:
            content = self._to_csv(documents, options)
        elif format == ExportFormat.JSON:
            content = self._to_json(documents, options)
        elif format == ExportFormat.MARKDOWN:
            content = self._to_markdown(documents, options)
        elif format == ExportFormat.BIBTEX:
            content = self._to_bibtex(documents)
        elif format == ExportFormat.ANNOTATED_BIBLIOGRAPHY:
            content = self._to_annotated_bibliography(documents, options)
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Generate filename if not provided
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{project_id}_{timestamp}{EXPORT_EXTENSIONS[format]}"

        return ExportResponse(
            content=content,
            filename=filename,
            content_type=EXPORT_CONTENT_TYPES[format],
            document_count=len(documents),
        )

    async def preview_export(
        self,
        project_id: int,
        format: ExportFormat,
        options: ExportOptions,
        limit: int = 5,
    ) -> tuple[str, int, int]:
        """
        Generate a preview of the export.

        Returns:
            Tuple of (preview_content, total_documents, preview_count)
        """
        # Get all documents count
        all_docs = await self._get_documents(project_id, None)
        total = len(all_docs)

        # Validate we have documents to preview
        if not all_docs:
            raise ValueError(
                "No documents to preview. Run a research job first to collect papers."
            )

        # Get limited documents for preview
        preview_docs = all_docs[:limit]

        # Generate preview content
        if format == ExportFormat.CSV:
            content = self._to_csv(preview_docs, options)
        elif format == ExportFormat.JSON:
            content = self._to_json(preview_docs, options)
        elif format == ExportFormat.MARKDOWN:
            content = self._to_markdown(preview_docs, options)
        elif format == ExportFormat.BIBTEX:
            content = self._to_bibtex(preview_docs)
        elif format == ExportFormat.ANNOTATED_BIBLIOGRAPHY:
            content = self._to_annotated_bibliography(preview_docs, options)
        else:
            content = ""

        return content, total, len(preview_docs)

    async def _get_documents(
        self,
        project_id: int,
        document_ids: list[int] | None = None,
    ) -> list[Document]:
        """Get documents for export."""
        query = select(Document).where(
            Document.project_id == project_id,
            Document.status == DocumentStatus.READY,
        )

        if document_ids:
            query = query.where(Document.id.in_(document_ids))

        query = query.order_by(Document.year.desc().nullslast(), Document.title)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _to_csv(self, documents: list[Document], options: ExportOptions) -> str:
        """Convert documents to CSV format."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        headers = ["ID", "Title", "Authors", "Year", "DOI", "Journal", "Type"]
        if options.include_abstracts:
            headers.append("Abstract")
        if options.include_summaries:
            headers.append("Summary")
        if options.include_key_findings:
            headers.append("Key Findings")
        if options.include_metadata:
            headers.extend(["Citation Count", "Open Access", "Tags", "Keywords"])

        writer.writerow(headers)

        # Data rows
        for doc in documents:
            row = [
                doc.id,
                doc.title,
                self._format_authors_simple(doc.authors),
                doc.year or "",
                doc.doi or "",
                self._get_journal_name(doc.journal),
                doc.document_type,
            ]

            if options.include_abstracts:
                row.append(doc.abstract or "")
            if options.include_summaries:
                row.append(doc.summary or "")
            if options.include_key_findings:
                findings = doc.key_findings or []
                if findings:
                    finding_strings = []
                    for f in findings:
                        if isinstance(f, dict):
                            finding_strings.append(f.get("finding", str(f)))
                        else:
                            finding_strings.append(str(f))
                    row.append("; ".join(finding_strings))
                else:
                    row.append("")
            if options.include_metadata:
                row.extend(
                    [
                        doc.citation_count or 0,
                        "Yes" if doc.is_open_access else "No",
                        ", ".join(doc.tags or []),
                        ", ".join(doc.keywords or []),
                    ]
                )

            writer.writerow(row)

        return output.getvalue()

    def _to_json(self, documents: list[Document], options: ExportOptions) -> str:
        """Convert documents to JSON format."""
        data = []

        for doc in documents:
            item = {
                "id": doc.id,
                "title": doc.title,
                "authors": doc.authors or [],
                "year": doc.year,
                "doi": doc.doi,
                "document_type": doc.document_type,
                "journal": doc.journal,
                "url": doc.url,
            }

            if options.include_abstracts:
                item["abstract"] = doc.abstract
            if options.include_summaries:
                item["summary"] = doc.summary
            if options.include_key_findings:
                item["key_findings"] = doc.key_findings
            if options.include_evidence:
                item["evidence_claims"] = doc.evidence_claims
            if options.include_metadata:
                item.update(
                    {
                        "citation_count": doc.citation_count,
                        "reference_count": doc.reference_count,
                        "is_open_access": doc.is_open_access,
                        "is_preprint": doc.is_preprint,
                        "tags": doc.tags,
                        "keywords": doc.keywords,
                        "subjects": doc.subjects,
                        "source_name": doc.source_name,
                        "created_at": (
                            doc.created_at.isoformat() if doc.created_at else None
                        ),
                    }
                )
            if options.include_full_text:
                item["full_text"] = doc.full_text

            data.append(item)

        return json.dumps(data, indent=2, ensure_ascii=False)

    def _to_markdown(self, documents: list[Document], options: ExportOptions) -> str:
        """Convert documents to Markdown format."""
        lines = []
        lines.append("# Document Export")
        lines.append("")
        lines.append(f"*Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*")
        lines.append(f"*Total documents: {len(documents)}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, doc in enumerate(documents, 1):
            lines.append(f"## {i}. {doc.title}")
            lines.append("")

            # Authors
            authors = self._format_authors_simple(doc.authors)
            if authors:
                lines.append(f"**Authors:** {authors}")

            # Publication info
            pub_info = []
            if doc.year:
                pub_info.append(str(doc.year))
            journal_name = self._get_journal_name(doc.journal)
            if journal_name:
                pub_info.append(journal_name)
            if pub_info:
                lines.append(f"**Published:** {', '.join(pub_info)}")

            # DOI
            if doc.doi:
                lines.append(f"**DOI:** [{doc.doi}](https://doi.org/{doc.doi})")

            # Tags
            if doc.tags:
                lines.append(f"**Tags:** {', '.join(doc.tags)}")

            lines.append("")

            # Abstract
            if options.include_abstracts and doc.abstract:
                lines.append("### Abstract")
                lines.append("")
                lines.append(doc.abstract)
                lines.append("")

            # Summary
            if options.include_summaries and doc.summary:
                lines.append("### Summary")
                lines.append("")
                lines.append(doc.summary)
                lines.append("")

            # Key findings
            if options.include_key_findings and doc.key_findings:
                lines.append("### Key Findings")
                lines.append("")
                for finding in doc.key_findings:
                    lines.append(f"- {finding}")
                lines.append("")

            # Evidence
            if options.include_evidence and doc.evidence_claims:
                lines.append("### Evidence Claims")
                lines.append("")
                for claim in doc.evidence_claims:
                    claim_text = claim.get("claim", "")
                    confidence = claim.get("confidence", 0)
                    lines.append(f"- {claim_text} (confidence: {confidence:.0%})")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _to_bibtex(self, documents: list[Document]) -> str:
        """Convert documents to BibTeX format."""
        entries = []

        for doc in documents:
            entry = self._format_bibtex_entry(doc)
            if entry:
                entries.append(entry)

        return "\n\n".join(entries)

    def _to_annotated_bibliography(
        self,
        documents: list[Document],
        options: ExportOptions,
    ) -> str:
        """Convert documents to annotated bibliography format."""
        lines = []
        lines.append("# Annotated Bibliography")
        lines.append("")
        lines.append(f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        for doc in documents:
            # Format citation
            citation = self._format_apa_citation(doc)
            lines.append(f"**{citation}**")
            lines.append("")

            # Annotation (summary or abstract)
            annotation = doc.summary or doc.abstract
            if annotation:
                lines.append(f"> {annotation}")
                lines.append("")

            # Key findings as bullet points
            if options.include_key_findings and doc.key_findings:
                lines.append("*Key findings:*")
                for finding in doc.key_findings:
                    lines.append(f"- {finding}")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _format_authors_simple(self, authors: list | None) -> str:
        """Format authors as a simple string."""
        if not authors:
            return ""

        names = []
        for author in authors:
            if isinstance(author, dict):
                names.append(author.get("name", "Unknown"))
            elif isinstance(author, str):
                names.append(author)

        if len(names) > 3:
            return f"{names[0]} et al."
        return ", ".join(names)

    def _get_journal_name(self, journal: dict | None) -> str:
        """Extract journal name from journal dict."""
        if not journal:
            return ""
        if isinstance(journal, dict):
            return journal.get("name", "")
        return ""

    def _format_bibtex_entry(self, doc: Document) -> str:
        """Format a single BibTeX entry."""
        # Generate citation key
        first_author = ""
        if doc.authors:
            author = doc.authors[0]
            if isinstance(author, dict):
                name = author.get("name", "Unknown")
            else:
                name = str(author)
            # Get last name
            parts = name.split()
            first_author = parts[-1].lower() if parts else "unknown"

        year = doc.year or "nodate"
        key = f"{first_author}{year}"

        # Determine entry type
        if doc.is_preprint:
            entry_type = "misc"
        elif doc.document_type == "book":
            entry_type = "book"
        elif doc.document_type == "book-chapter":
            entry_type = "incollection"
        elif doc.document_type == "proceedings-article":
            entry_type = "inproceedings"
        else:
            entry_type = "article"

        lines = [f"@{entry_type}{{{key},"]

        # Title
        lines.append(f"  title = {{{doc.title}}},")

        # Authors
        if doc.authors:
            author_names = []
            for author in doc.authors:
                if isinstance(author, dict):
                    author_names.append(author.get("name", "Unknown"))
                else:
                    author_names.append(str(author))
            lines.append(f"  author = {{{' and '.join(author_names)}}},")

        # Year
        if doc.year:
            lines.append(f"  year = {{{doc.year}}},")

        # Journal
        journal_name = self._get_journal_name(doc.journal)
        if journal_name and entry_type == "article":
            lines.append(f"  journal = {{{journal_name}}},")

        # Volume, issue, pages
        if doc.journal:
            if doc.journal.get("volume"):
                lines.append(f"  volume = {{{doc.journal['volume']}}},")
            if doc.journal.get("issue"):
                lines.append(f"  number = {{{doc.journal['issue']}}},")
            if doc.journal.get("pages"):
                lines.append(f"  pages = {{{doc.journal['pages']}}},")

        # DOI
        if doc.doi:
            lines.append(f"  doi = {{{doc.doi}}},")

        # URL
        if doc.url:
            lines.append(f"  url = {{{doc.url}}},")

        # Abstract
        if doc.abstract:
            # Escape special characters
            abstract = doc.abstract.replace("{", "\\{").replace("}", "\\}")
            lines.append(f"  abstract = {{{abstract}}},")

        # Keywords
        if doc.keywords:
            lines.append(f"  keywords = {{{', '.join(doc.keywords)}}},")

        lines.append("}")

        return "\n".join(lines)

    def _format_apa_citation(self, doc: Document) -> str:
        """Format a basic APA citation."""
        parts = []

        # Authors
        if doc.authors:
            author_names = []
            for author in doc.authors[:3]:  # Max 3 authors
                if isinstance(author, dict):
                    name = author.get("name", "Unknown")
                else:
                    name = str(author)
                # Convert to "Last, F." format
                name_parts = name.split()
                if len(name_parts) >= 2:
                    last = name_parts[-1]
                    first_initial = name_parts[0][0]
                    author_names.append(f"{last}, {first_initial}.")
                else:
                    author_names.append(name)

            if len(doc.authors) > 3:
                author_str = ", ".join(author_names) + ", et al."
            else:
                if len(author_names) == 2:
                    author_str = " & ".join(author_names)
                elif len(author_names) > 2:
                    author_str = (
                        ", ".join(author_names[:-1]) + ", & " + author_names[-1]
                    )
                else:
                    author_str = author_names[0] if author_names else "Unknown"
            parts.append(author_str)

        # Year
        if doc.year:
            parts.append(f"({doc.year}).")
        else:
            parts.append("(n.d.).")

        # Title
        parts.append(f"{doc.title}.")

        # Journal
        journal_name = self._get_journal_name(doc.journal)
        if journal_name:
            journal_str = f"*{journal_name}*"
            if doc.journal:
                if doc.journal.get("volume"):
                    journal_str += f", *{doc.journal['volume']}*"
                if doc.journal.get("issue"):
                    journal_str += f"({doc.journal['issue']})"
                if doc.journal.get("pages"):
                    journal_str += f", {doc.journal['pages']}"
            parts.append(journal_str + ".")

        # DOI
        if doc.doi:
            parts.append(f"https://doi.org/{doc.doi}")

        return " ".join(parts)


def get_export_service(db: AsyncSession) -> ExportService:
    """Get an export service instance."""
    return ExportService(db)
