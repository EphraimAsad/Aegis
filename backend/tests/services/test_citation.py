"""Tests for the citation service."""

from unittest.mock import MagicMock

import pytest

from app.schemas.citation import CitationStyle
from app.services.citation import CitationService


class MockDocument:
    """Mock document for testing citations."""

    def __init__(
        self,
        id: int = 1,
        title: str = "Test Paper Title",
        authors: list | None = None,
        year: int | None = 2023,
        doi: str | None = "10.1234/test.2023",
        journal: dict | None = None,
        url: str | None = None,
        document_type: str | None = "journal-article",
        is_preprint: bool = False,
    ):
        self.id = id
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
        self.url = url
        self.document_type = document_type
        self.is_preprint = is_preprint


class TestCitationFormatting:
    """Tests for citation formatting methods."""

    @pytest.fixture
    def service(self) -> CitationService:
        """Create service with mock db."""
        mock_db = MagicMock()
        return CitationService(mock_db)

    @pytest.fixture
    def document(self) -> MockDocument:
        """Create test document."""
        return MockDocument()

    def test_format_apa(self, service: CitationService, document: MockDocument) -> None:
        """Test APA citation formatting."""
        citation = service._format_apa(document)

        # Should contain author last names
        assert "Smith" in citation
        assert "Doe" in citation
        # Should contain year
        assert "2023" in citation
        # Should contain title
        assert "Test Paper Title" in citation
        # Should contain DOI
        assert "10.1234/test.2023" in citation

    def test_format_apa_no_year(self, service: CitationService) -> None:
        """Test APA formatting with no year."""
        doc = MockDocument(year=None)
        citation = service._format_apa(doc)
        assert "n.d." in citation

    def test_format_apa_single_author(self, service: CitationService) -> None:
        """Test APA formatting with single author."""
        doc = MockDocument(authors=[{"name": "John Smith"}])
        citation = service._format_apa(doc)
        assert "Smith, J." in citation
        assert "&" not in citation

    def test_format_apa_many_authors(self, service: CitationService) -> None:
        """Test APA formatting with many authors."""
        doc = MockDocument(authors=[{"name": f"Author {i}"} for i in range(25)])
        citation = service._format_apa(doc)
        # Should use ellipsis for 20+ authors
        assert "..." in citation

    def test_format_chicago(
        self, service: CitationService, document: MockDocument
    ) -> None:
        """Test Chicago citation formatting."""
        citation = service._format_chicago(document)

        # Should contain author names
        assert "Smith" in citation
        # Title should be in quotes (may use smart quotes)
        assert "Test Paper Title" in citation
        # Should contain year
        assert "2023" in citation

    def test_format_mla(self, service: CitationService, document: MockDocument) -> None:
        """Test MLA citation formatting."""
        citation = service._format_mla(document)

        # First author should be last name first
        assert "Smith" in citation
        # Title should be present (may use smart quotes)
        assert "Test Paper Title" in citation
        # Should include volume notation
        assert "vol." in citation

    def test_format_mla_single_author(self, service: CitationService) -> None:
        """Test MLA with single author."""
        doc = MockDocument(authors=[{"name": "Jane Doe"}])
        citation = service._format_mla(doc)
        assert "Doe, Jane" in citation
        assert "et al." not in citation

    def test_format_mla_three_plus_authors(self, service: CitationService) -> None:
        """Test MLA with 3+ authors uses et al."""
        doc = MockDocument(
            authors=[
                {"name": "First Author"},
                {"name": "Second Author"},
                {"name": "Third Author"},
            ]
        )
        citation = service._format_mla(doc)
        assert "et al." in citation

    def test_format_harvard(
        self, service: CitationService, document: MockDocument
    ) -> None:
        """Test Harvard citation formatting."""
        citation = service._format_harvard(document)

        # Should contain author names
        assert "Smith" in citation
        # Year in parentheses
        assert "(2023)" in citation
        # Title in single quotes
        assert "'Test Paper Title'" in citation

    def test_format_ieee(
        self, service: CitationService, document: MockDocument
    ) -> None:
        """Test IEEE citation formatting."""
        citation = service._format_ieee(document)

        # IEEE uses initials first
        assert "J." in citation  # First initial
        assert "Smith" in citation
        # Title should be present (may use smart quotes)
        assert "Test Paper Title" in citation
        # Volume notation
        assert "vol." in citation

    def test_format_bibtex(
        self, service: CitationService, document: MockDocument
    ) -> None:
        """Test BibTeX entry formatting."""
        citation = service._format_bibtex(document)

        # Should be a valid BibTeX entry
        assert citation.startswith("@article{")
        assert citation.endswith("}")
        # Should contain key fields
        assert "title = {Test Paper Title}" in citation
        assert "author = {" in citation
        assert "year = {2023}" in citation
        assert "doi = {10.1234/test.2023}" in citation
        assert "journal = {Journal of Testing}" in citation

    def test_format_bibtex_preprint(self, service: CitationService) -> None:
        """Test BibTeX for preprint uses misc type."""
        doc = MockDocument(is_preprint=True)
        citation = service._format_bibtex(doc)
        assert citation.startswith("@misc{")

    def test_format_bibtex_book(self, service: CitationService) -> None:
        """Test BibTeX for book uses book type."""
        doc = MockDocument(document_type="book")
        citation = service._format_bibtex(doc)
        assert citation.startswith("@book{")

    def test_format_bibtex_proceedings(self, service: CitationService) -> None:
        """Test BibTeX for proceedings article."""
        doc = MockDocument(document_type="proceedings-article")
        citation = service._format_bibtex(doc)
        assert citation.startswith("@inproceedings{")

    def test_format_citation_all_styles(
        self, service: CitationService, document: MockDocument
    ) -> None:
        """Test that all citation styles work."""
        for style in CitationStyle:
            citation = service._format_citation(document, style)
            assert citation is not None
            assert len(citation) > 0

    def test_no_authors(self, service: CitationService) -> None:
        """Test formatting with no authors."""
        doc = MockDocument(authors=None)
        citation = service._format_apa(doc)
        # Should still produce valid citation
        assert "Test Paper Title" in citation

    def test_no_journal(self, service: CitationService) -> None:
        """Test formatting with no journal."""
        doc = MockDocument(journal=None)
        citation = service._format_apa(doc)
        # Should still produce valid citation
        assert "Test Paper Title" in citation

    def test_no_doi(self, service: CitationService) -> None:
        """Test formatting with no DOI."""
        doc = MockDocument(doi=None)
        citation = service._format_apa(doc)
        # Should not contain DOI
        assert "doi.org" not in citation

    def test_string_author_format(self, service: CitationService) -> None:
        """Test formatting with string authors (not dict)."""
        doc = MockDocument(authors=["John Smith", "Jane Doe"])
        citation = service._format_apa(doc)
        assert "Smith" in citation

    def test_get_available_styles(self, service: CitationService) -> None:
        """Test getting available citation styles."""
        styles = service.get_available_styles()
        assert styles is not None
        assert len(styles.styles) == len(CitationStyle)

    def test_get_raw_components(
        self, service: CitationService, document: MockDocument
    ) -> None:
        """Test getting raw citation components."""
        components = service._get_raw_components(document)
        assert components["title"] == "Test Paper Title"
        assert components["year"] == 2023
        assert components["doi"] == "10.1234/test.2023"
        assert len(components["authors"]) == 2


class TestAuthorFormatting:
    """Tests for author name formatting across styles."""

    @pytest.fixture
    def service(self) -> CitationService:
        """Create service with mock db."""
        mock_db = MagicMock()
        return CitationService(mock_db)

    def test_apa_two_authors(self, service: CitationService) -> None:
        """Test APA with exactly two authors."""
        authors = [{"name": "John Smith"}, {"name": "Jane Doe"}]
        formatted = service._format_authors_apa(authors)
        assert "&" in formatted
        assert "Smith" in formatted
        assert "Doe" in formatted

    def test_apa_three_authors(self, service: CitationService) -> None:
        """Test APA with three authors."""
        authors = [
            {"name": "John Smith"},
            {"name": "Jane Doe"},
            {"name": "Bob Johnson"},
        ]
        formatted = service._format_authors_apa(authors)
        assert "&" in formatted  # Final author with &
        assert "Smith" in formatted
        assert "Doe" in formatted
        assert "Johnson" in formatted

    def test_chicago_author_format(self, service: CitationService) -> None:
        """Test Chicago author formatting."""
        authors = [{"name": "John Smith"}, {"name": "Jane Doe"}]
        formatted = service._format_authors_chicago(authors)
        # Should use "and" not "&"
        assert " and " in formatted
        # First author: Last, First
        assert "Smith, John" in formatted

    def test_ieee_initials_first(self, service: CitationService) -> None:
        """Test IEEE puts initials first."""
        authors = [{"name": "John Robert Smith"}]
        formatted = service._format_authors_ieee(authors)
        # Should have initials before last name
        assert "J." in formatted
        assert "R." in formatted
        assert "Smith" in formatted

    def test_harvard_et_al_threshold(self, service: CitationService) -> None:
        """Test Harvard uses et al. for 4+ authors."""
        authors = [{"name": f"Author {i}"} for i in range(5)]
        formatted = service._format_authors_harvard(authors)
        assert "et al." in formatted

    def test_get_author_name_dict(self, service: CitationService) -> None:
        """Test extracting name from dict."""
        name = service._get_author_name({"name": "Test Author"})
        assert name == "Test Author"

    def test_get_author_name_string(self, service: CitationService) -> None:
        """Test extracting name from string."""
        name = service._get_author_name("Test Author")
        assert name == "Test Author"
