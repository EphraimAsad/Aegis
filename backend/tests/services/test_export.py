"""Tests for the export service."""

import json
from unittest.mock import MagicMock

import pytest

from app.schemas.export import ExportOptions
from app.services.export import ExportService


class MockDocument:
    """Mock document for testing exports."""

    def __init__(
        self,
        id: int = 1,
        project_id: int = 1,
        title: str = "Test Paper Title",
        authors: list | None = None,
        year: int | None = 2023,
        doi: str | None = "10.1234/test.2023",
        journal: dict | None = None,
        abstract: str | None = "This is the abstract.",
        summary: str | None = "This is the summary.",
        document_type: str | None = "journal-article",
        url: str | None = "https://example.com/paper",
        is_open_access: bool = True,
        citation_count: int | None = 42,
        tags: list | None = None,
        keywords: list | None = None,
        key_findings: list | None = None,
        evidence_snippets: list | None = None,
        evidence_claims: list | None = None,
        is_preprint: bool = False,
    ):
        self.id = id
        self.project_id = project_id
        self.title = title
        self.authors = authors or [
            {"name": "John Smith"},
            {"name": "Jane Doe"},
        ]
        self.year = year
        self.doi = doi
        self.journal = journal or {
            "name": "Journal of Testing",
            "volume": "10",
            "issue": "2",
            "pages": "123-145",
        }
        self.abstract = abstract
        self.summary = summary
        self.document_type = document_type
        self.url = url
        self.is_open_access = is_open_access
        self.citation_count = citation_count
        self.tags = tags or ["machine-learning", "testing"]
        self.keywords = keywords or ["ML", "AI"]
        self.key_findings = key_findings or [
            "Finding 1: Important result.",
            "Finding 2: Another result.",
        ]
        self.evidence_snippets = evidence_snippets or [
            {
                "text": "Evidence quote here.",
                "context": "Methods section",
                "relevance": 0.85,
            }
        ]
        self.evidence_claims = evidence_claims or [
            {
                "claim": "Evidence quote here.",
                "source_text": "Methods section",
                "confidence": 0.85,
            }
        ]
        self.is_preprint = is_preprint
        # Additional fields needed by export service
        self.reference_count = 10
        self.subjects = ["Computer Science"]
        self.source_name = "crossref"
        self.created_at = None
        self.full_text = None


class TestExportFormatting:
    """Tests for export formatting methods."""

    @pytest.fixture
    def service(self) -> ExportService:
        """Create service with mock db."""
        mock_db = MagicMock()
        return ExportService(mock_db)

    @pytest.fixture
    def documents(self) -> list[MockDocument]:
        """Create test documents."""
        return [
            MockDocument(id=1, title="First Paper", year=2023),
            MockDocument(id=2, title="Second Paper", year=2022),
            MockDocument(id=3, title="Third Paper", year=2021),
        ]

    @pytest.fixture
    def options(self) -> ExportOptions:
        """Create default export options."""
        return ExportOptions(
            include_abstracts=True,
            include_summaries=True,
            include_key_findings=True,
            include_evidence=True,
            include_metadata=True,
        )

    def test_csv_export_basic(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test basic CSV export."""
        csv_content = service._to_csv(documents, options)

        # Should be valid CSV
        assert csv_content is not None
        lines = csv_content.strip().split("\n")
        assert len(lines) == 4  # Header + 3 documents

        # Check header
        header = lines[0]
        assert "Title" in header
        assert "Authors" in header
        assert "Year" in header
        assert "DOI" in header

    def test_csv_export_contains_data(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test CSV contains document data."""
        csv_content = service._to_csv(documents, options)

        assert "First Paper" in csv_content
        assert "Second Paper" in csv_content
        assert "2023" in csv_content
        assert "10.1234/test.2023" in csv_content

    def test_csv_export_with_abstracts(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test CSV includes abstracts when requested."""
        options = ExportOptions(include_abstracts=True)
        csv_content = service._to_csv(documents, options)

        assert "Abstract" in csv_content
        assert "This is the abstract" in csv_content

    def test_csv_export_without_abstracts(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test CSV excludes abstracts when not requested."""
        options = ExportOptions(include_abstracts=False)
        csv_content = service._to_csv(documents, options)

        # Abstract should not be a column header
        lines = csv_content.strip().split("\n")
        header = lines[0]
        # Count occurrences of "Abstract" in header
        # Should not appear as a separate column
        assert header.count(",Abstract,") == 0 or "Abstract" not in header

    def test_json_export_basic(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test basic JSON export."""
        json_content = service._to_json(documents, options)

        # Should be valid JSON (returns a list of documents)
        parsed = json.loads(json_content)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

    def test_json_export_structure(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test JSON export structure."""
        json_content = service._to_json(documents, options)
        parsed = json.loads(json_content)

        doc = parsed[0]
        assert "id" in doc
        assert "title" in doc
        assert "authors" in doc
        assert "year" in doc

    def test_json_export_metadata(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test JSON export includes document metadata when requested."""
        json_content = service._to_json(documents, options)
        parsed = json.loads(json_content)

        # With include_metadata, each document should have metadata fields
        doc = parsed[0]
        assert "citation_count" in doc
        assert "is_open_access" in doc

    def test_markdown_export_basic(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test basic Markdown export."""
        md_content = service._to_markdown(documents, options)

        # Should contain markdown formatting
        assert md_content is not None
        assert "# " in md_content or "## " in md_content
        assert "First Paper" in md_content

    def test_markdown_export_includes_authors(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test Markdown includes author information."""
        md_content = service._to_markdown(documents, options)

        # Should contain author info
        assert "John Smith" in md_content or "Smith" in md_content

    def test_markdown_export_includes_abstract(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test Markdown includes abstracts."""
        options = ExportOptions(include_abstracts=True)
        md_content = service._to_markdown(documents, options)

        assert "abstract" in md_content.lower() or "This is the abstract" in md_content

    def test_bibtex_export_basic(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test basic BibTeX export."""
        bibtex_content = service._to_bibtex(documents)

        # Should contain BibTeX entries
        assert bibtex_content is not None
        assert "@article{" in bibtex_content or "@misc{" in bibtex_content
        assert "title = {" in bibtex_content

    def test_bibtex_export_contains_all_documents(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test BibTeX contains all documents."""
        bibtex_content = service._to_bibtex(documents)

        assert "First Paper" in bibtex_content
        assert "Second Paper" in bibtex_content
        assert "Third Paper" in bibtex_content

    def test_bibtex_export_includes_doi(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test BibTeX includes DOI."""
        bibtex_content = service._to_bibtex(documents)

        assert "doi = {10.1234/test.2023}" in bibtex_content

    def test_annotated_bibliography_basic(
        self,
        service: ExportService,
        documents: list[MockDocument],
        options: ExportOptions,
    ) -> None:
        """Test annotated bibliography export."""
        content = service._to_annotated_bibliography(documents, options)

        # Should contain formatted citations and annotations
        assert content is not None
        assert len(content) > 0
        assert "First Paper" in content

    def test_annotated_bibliography_includes_summary(
        self, service: ExportService, documents: list[MockDocument]
    ) -> None:
        """Test annotated bibliography includes summaries."""
        options = ExportOptions(include_summaries=True)
        content = service._to_annotated_bibliography(documents, options)

        assert "summary" in content.lower() or "This is the summary" in content

    def test_empty_documents_csv(
        self, service: ExportService, options: ExportOptions
    ) -> None:
        """Test CSV export with empty document list."""
        csv_content = service._to_csv([], options)

        # Should have at least a header
        lines = csv_content.strip().split("\n")
        assert len(lines) >= 1
        assert "Title" in lines[0]

    def test_empty_documents_json(
        self, service: ExportService, options: ExportOptions
    ) -> None:
        """Test JSON export with empty document list."""
        json_content = service._to_json([], options)
        parsed = json.loads(json_content)

        assert parsed == []

    def test_empty_documents_markdown(
        self, service: ExportService, options: ExportOptions
    ) -> None:
        """Test Markdown export with empty document list."""
        md_content = service._to_markdown([], options)

        # Should still produce valid output
        assert md_content is not None

    def test_document_with_missing_fields(
        self, service: ExportService, options: ExportOptions
    ) -> None:
        """Test export handles documents with missing fields."""
        doc = MockDocument(
            authors=None,
            year=None,
            doi=None,
            journal=None,
            abstract=None,
            summary=None,
        )

        # Should not raise errors
        csv_content = service._to_csv([doc], options)
        assert "Test Paper Title" in csv_content

        json_content = service._to_json([doc], options)
        parsed = json.loads(json_content)
        assert parsed[0]["title"] == "Test Paper Title"


class TestExportOptions:
    """Tests for export options handling."""

    @pytest.fixture
    def service(self) -> ExportService:
        """Create service with mock db."""
        mock_db = MagicMock()
        return ExportService(mock_db)

    @pytest.fixture
    def document(self) -> MockDocument:
        """Create test document."""
        return MockDocument()

    def test_options_include_key_findings(self, service: ExportService) -> None:
        """Test key findings are included when requested."""
        doc = MockDocument()
        options = ExportOptions(include_key_findings=True)

        md_content = service._to_markdown([doc], options)
        # Should contain key findings section or findings content
        assert "Finding" in md_content or "findings" in md_content.lower()

    def test_options_include_evidence(self, service: ExportService) -> None:
        """Test evidence is included in JSON when requested."""
        doc = MockDocument()
        options = ExportOptions(include_evidence=True)

        json_content = service._to_json([doc], options)
        parsed = json.loads(json_content)
        # Should contain evidence_claims field
        assert "evidence_claims" in parsed[0]
        assert len(parsed[0]["evidence_claims"]) > 0

    def test_options_include_metadata_csv(self, service: ExportService) -> None:
        """Test metadata columns in CSV."""
        doc = MockDocument()
        options = ExportOptions(include_metadata=True)

        csv_content = service._to_csv([doc], options)
        lines = csv_content.strip().split("\n")
        header = lines[0]

        # Should have metadata columns
        assert "Citation Count" in header or "Tags" in header
