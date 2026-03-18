"""Service for formatting citations in various styles."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.citation import (
    CITATION_STYLES_INFO,
    Citation,
    CitationResponse,
    CitationStyle,
    CitationStylesResponse,
    DocumentCitations,
)


class CitationService:
    """Service for formatting document citations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def format_citations(
        self,
        document_ids: list[int],
        style: CitationStyle,
    ) -> CitationResponse:
        """
        Format citations for multiple documents.

        Args:
            document_ids: List of document IDs
            style: Citation style to use

        Returns:
            CitationResponse with formatted citations
        """
        documents = await self._get_documents(document_ids)

        citations = []
        for doc in documents:
            formatted = self._format_citation(doc, style)
            citations.append(Citation(
                document_id=doc.id,
                title=doc.title,
                style=style,
                formatted=formatted,
                raw_components=self._get_raw_components(doc),
            ))

        return CitationResponse(
            citations=citations,
            style=style,
            count=len(citations),
        )

    async def get_document_citations(
        self,
        document_id: int,
        styles: list[CitationStyle] | None = None,
    ) -> DocumentCitations:
        """
        Get all citation formats for a single document.

        Args:
            document_id: Document ID
            styles: Specific styles (None = all styles)

        Returns:
            DocumentCitations with all formats
        """
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        if styles is None:
            styles = list(CitationStyle)

        citations = {}
        for style in styles:
            citations[style.value] = self._format_citation(document, style)

        return DocumentCitations(
            document_id=document.id,
            title=document.title,
            citations=citations,
        )

    def get_available_styles(self) -> CitationStylesResponse:
        """Get list of available citation styles."""
        return CitationStylesResponse(styles=CITATION_STYLES_INFO)

    async def _get_documents(self, document_ids: list[int]) -> list[Document]:
        """Get documents by IDs."""
        result = await self.db.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        return list(result.scalars().all())

    def _format_citation(self, doc: Document, style: CitationStyle) -> str:
        """Format a citation in the specified style."""
        if style == CitationStyle.APA:
            return self._format_apa(doc)
        elif style == CitationStyle.CHICAGO:
            return self._format_chicago(doc)
        elif style == CitationStyle.MLA:
            return self._format_mla(doc)
        elif style == CitationStyle.HARVARD:
            return self._format_harvard(doc)
        elif style == CitationStyle.IEEE:
            return self._format_ieee(doc)
        elif style == CitationStyle.BIBTEX:
            return self._format_bibtex(doc)
        else:
            return self._format_apa(doc)

    def _format_apa(self, doc: Document) -> str:
        """Format citation in APA 7th edition style."""
        parts = []

        # Authors
        authors = self._format_authors_apa(doc.authors)
        if authors:
            parts.append(authors)

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

    def _format_chicago(self, doc: Document) -> str:
        """Format citation in Chicago style (author-date)."""
        parts = []

        # Authors (Last, First format)
        authors = self._format_authors_chicago(doc.authors)
        if authors:
            parts.append(authors)

        # Year
        if doc.year:
            parts.append(f"{doc.year}.")

        # Title in quotes
        parts.append(f'"{doc.title}."')

        # Journal in italics
        journal_name = self._get_journal_name(doc.journal)
        if journal_name:
            journal_str = f"*{journal_name}*"
            if doc.journal:
                vol_issue = []
                if doc.journal.get("volume"):
                    vol_issue.append(doc.journal["volume"])
                if doc.journal.get("issue"):
                    vol_issue.append(f"no. {doc.journal['issue']}")
                if vol_issue:
                    journal_str += " " + ", ".join(vol_issue)
                if doc.journal.get("pages"):
                    journal_str += f": {doc.journal['pages']}"
            parts.append(journal_str + ".")

        # DOI
        if doc.doi:
            parts.append(f"https://doi.org/{doc.doi}.")

        return " ".join(parts)

    def _format_mla(self, doc: Document) -> str:
        """Format citation in MLA 9th edition style."""
        parts = []

        # Authors
        authors = self._format_authors_mla(doc.authors)
        if authors:
            parts.append(authors)

        # Title in quotes
        parts.append(f'"{doc.title}."')

        # Journal in italics
        journal_name = self._get_journal_name(doc.journal)
        if journal_name:
            journal_str = f"*{journal_name}*"
            if doc.journal:
                if doc.journal.get("volume"):
                    journal_str += f", vol. {doc.journal['volume']}"
                if doc.journal.get("issue"):
                    journal_str += f", no. {doc.journal['issue']}"
            if doc.year:
                journal_str += f", {doc.year}"
            if doc.journal and doc.journal.get("pages"):
                journal_str += f", pp. {doc.journal['pages']}"
            parts.append(journal_str + ".")

        # DOI
        if doc.doi:
            parts.append(f"https://doi.org/{doc.doi}.")

        return " ".join(parts)

    def _format_harvard(self, doc: Document) -> str:
        """Format citation in Harvard style."""
        parts = []

        # Authors
        authors = self._format_authors_harvard(doc.authors)
        if authors:
            parts.append(authors)

        # Year
        if doc.year:
            parts.append(f"({doc.year})")

        # Title in single quotes
        parts.append(f"'{doc.title}',")

        # Journal in italics
        journal_name = self._get_journal_name(doc.journal)
        if journal_name:
            journal_str = f"*{journal_name}*"
            if doc.journal:
                if doc.journal.get("volume"):
                    journal_str += f", {doc.journal['volume']}"
                if doc.journal.get("issue"):
                    journal_str += f"({doc.journal['issue']})"
                if doc.journal.get("pages"):
                    journal_str += f", pp. {doc.journal['pages']}"
            parts.append(journal_str + ".")

        # DOI
        if doc.doi:
            parts.append(f"doi: {doc.doi}")

        return " ".join(parts)

    def _format_ieee(self, doc: Document) -> str:
        """Format citation in IEEE style."""
        parts = []

        # Authors (initials first)
        authors = self._format_authors_ieee(doc.authors)
        if authors:
            parts.append(authors + ",")

        # Title in quotes
        parts.append(f'"{doc.title},"')

        # Journal in italics
        journal_name = self._get_journal_name(doc.journal)
        if journal_name:
            journal_str = f"*{journal_name}*"
            if doc.journal:
                if doc.journal.get("volume"):
                    journal_str += f", vol. {doc.journal['volume']}"
                if doc.journal.get("issue"):
                    journal_str += f", no. {doc.journal['issue']}"
                if doc.journal.get("pages"):
                    journal_str += f", pp. {doc.journal['pages']}"
            if doc.year:
                journal_str += f", {doc.year}"
            parts.append(journal_str + ".")

        # DOI
        if doc.doi:
            parts.append(f"doi: {doc.doi}.")

        return " ".join(parts)

    def _format_bibtex(self, doc: Document) -> str:
        """Format citation as BibTeX entry."""
        # Generate citation key
        first_author = "unknown"
        if doc.authors:
            author = doc.authors[0]
            if isinstance(author, dict):
                name = author.get("name", "Unknown")
            else:
                name = str(author)
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

        # Required fields
        lines.append(f"  title = {{{doc.title}}},")

        if doc.authors:
            author_names = []
            for author in doc.authors:
                if isinstance(author, dict):
                    author_names.append(author.get("name", "Unknown"))
                else:
                    author_names.append(str(author))
            lines.append(f"  author = {{{' and '.join(author_names)}}},")

        if doc.year:
            lines.append(f"  year = {{{doc.year}}},")

        # Optional fields
        journal_name = self._get_journal_name(doc.journal)
        if journal_name and entry_type == "article":
            lines.append(f"  journal = {{{journal_name}}},")

        if doc.journal:
            if doc.journal.get("volume"):
                lines.append(f"  volume = {{{doc.journal['volume']}}},")
            if doc.journal.get("issue"):
                lines.append(f"  number = {{{doc.journal['issue']}}},")
            if doc.journal.get("pages"):
                lines.append(f"  pages = {{{doc.journal['pages']}}},")

        if doc.doi:
            lines.append(f"  doi = {{{doc.doi}}},")

        if doc.url:
            lines.append(f"  url = {{{doc.url}}},")

        lines.append("}")

        return "\n".join(lines)

    def _format_authors_apa(self, authors: list | None) -> str:
        """Format authors for APA style."""
        if not authors:
            return ""

        formatted = []
        for author in authors[:20]:  # APA allows up to 20 authors
            name = self._get_author_name(author)
            parts = name.split()
            if len(parts) >= 2:
                last = parts[-1]
                initials = "".join(f"{p[0]}." for p in parts[:-1])
                formatted.append(f"{last}, {initials}")
            else:
                formatted.append(name)

        if len(authors) > 20:
            # Use ellipsis for more than 20 authors
            return ", ".join(formatted[:19]) + ", ... " + formatted[-1]
        elif len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]}, & {formatted[1]}"
        else:
            return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"

    def _format_authors_chicago(self, authors: list | None) -> str:
        """Format authors for Chicago style."""
        if not authors:
            return ""

        formatted = []
        for author in authors[:10]:
            name = self._get_author_name(author)
            parts = name.split()
            if len(parts) >= 2:
                last = parts[-1]
                first = " ".join(parts[:-1])
                formatted.append(f"{last}, {first}")
            else:
                formatted.append(name)

        if len(formatted) == 1:
            return formatted[0] + "."
        elif len(formatted) == 2:
            return f"{formatted[0]}, and {formatted[1]}."
        else:
            return ", ".join(formatted[:-1]) + f", and {formatted[-1]}."

    def _format_authors_mla(self, authors: list | None) -> str:
        """Format authors for MLA style."""
        if not authors:
            return ""

        first_author = self._get_author_name(authors[0])
        parts = first_author.split()
        if len(parts) >= 2:
            first_formatted = f"{parts[-1]}, {' '.join(parts[:-1])}"
        else:
            first_formatted = first_author

        if len(authors) == 1:
            return first_formatted + "."
        elif len(authors) == 2:
            second = self._get_author_name(authors[1])
            return f"{first_formatted}, and {second}."
        else:
            return first_formatted + ", et al."

    def _format_authors_harvard(self, authors: list | None) -> str:
        """Format authors for Harvard style."""
        if not authors:
            return ""

        formatted = []
        for author in authors[:3]:
            name = self._get_author_name(author)
            parts = name.split()
            if len(parts) >= 2:
                last = parts[-1]
                initials = "".join(f"{p[0]}." for p in parts[:-1])
                formatted.append(f"{last}, {initials}")
            else:
                formatted.append(name)

        if len(authors) > 3:
            return formatted[0] + " et al."
        elif len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]} and {formatted[1]}"
        else:
            return ", ".join(formatted[:-1]) + f" and {formatted[-1]}"

    def _format_authors_ieee(self, authors: list | None) -> str:
        """Format authors for IEEE style."""
        if not authors:
            return ""

        formatted = []
        for author in authors[:6]:
            name = self._get_author_name(author)
            parts = name.split()
            if len(parts) >= 2:
                initials = " ".join(f"{p[0]}." for p in parts[:-1])
                last = parts[-1]
                formatted.append(f"{initials} {last}")
            else:
                formatted.append(name)

        if len(authors) > 6:
            return ", ".join(formatted) + ", et al."
        elif len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]} and {formatted[1]}"
        else:
            return ", ".join(formatted[:-1]) + f", and {formatted[-1]}"

    def _get_author_name(self, author) -> str:
        """Extract author name from various formats."""
        if isinstance(author, dict):
            return author.get("name", "Unknown")
        return str(author)

    def _get_journal_name(self, journal: dict | None) -> str:
        """Extract journal name from journal dict."""
        if not journal:
            return ""
        if isinstance(journal, dict):
            return journal.get("name", "")
        return ""

    def _get_raw_components(self, doc: Document) -> dict:
        """Get raw citation components for a document."""
        return {
            "authors": doc.authors,
            "year": doc.year,
            "title": doc.title,
            "journal": doc.journal,
            "doi": doc.doi,
            "url": doc.url,
            "document_type": doc.document_type,
        }


def get_citation_service(db: AsyncSession) -> CitationService:
    """Get a citation service instance."""
    return CitationService(db)
