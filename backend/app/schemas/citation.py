"""Schemas for citation formatting."""

from enum import Enum

from pydantic import BaseModel, Field


class CitationStyle(str, Enum):
    """Supported citation styles."""

    APA = "apa"  # APA 7th Edition
    CHICAGO = "chicago"  # Chicago Manual of Style
    MLA = "mla"  # MLA 9th Edition
    HARVARD = "harvard"  # Harvard style
    IEEE = "ieee"  # IEEE style
    BIBTEX = "bibtex"  # BibTeX format


class CitationStyleInfo(BaseModel):
    """Information about a citation style."""

    id: CitationStyle
    name: str
    description: str
    example: str


class CitationRequest(BaseModel):
    """Request to format citations."""

    document_ids: list[int]
    style: CitationStyle = CitationStyle.APA


class Citation(BaseModel):
    """A formatted citation."""

    document_id: int
    title: str
    style: CitationStyle
    formatted: str
    raw_components: dict | None = None


class CitationResponse(BaseModel):
    """Response with formatted citations."""

    citations: list[Citation]
    style: CitationStyle
    count: int


class DocumentCitations(BaseModel):
    """All citation formats for a single document."""

    document_id: int
    title: str
    citations: dict[str, str]  # style -> formatted citation


class CitationStylesResponse(BaseModel):
    """List of available citation styles."""

    styles: list[CitationStyleInfo]


# Citation style metadata
CITATION_STYLES_INFO = [
    CitationStyleInfo(
        id=CitationStyle.APA,
        name="APA 7th Edition",
        description="American Psychological Association format, commonly used in social sciences",
        example="Author, A. A. (Year). Title of article. Journal Name, volume(issue), pages. https://doi.org/xxx",
    ),
    CitationStyleInfo(
        id=CitationStyle.CHICAGO,
        name="Chicago Manual of Style",
        description="Widely used in humanities and some social sciences",
        example='Author Last, First. "Article Title." Journal Name Volume, no. Issue (Year): pages.',
    ),
    CitationStyleInfo(
        id=CitationStyle.MLA,
        name="MLA 9th Edition",
        description="Modern Language Association format, used in humanities",
        example='Author Last, First. "Title of Article." Journal Name, vol. X, no. X, Year, pp. X-X.',
    ),
    CitationStyleInfo(
        id=CitationStyle.HARVARD,
        name="Harvard Style",
        description="Author-date system popular in UK and Australia",
        example="Author, A.A. (Year) 'Title of article', Journal Name, Volume(Issue), pp. pages.",
    ),
    CitationStyleInfo(
        id=CitationStyle.IEEE,
        name="IEEE Style",
        description="Institute of Electrical and Electronics Engineers format, used in technical fields",
        example='[1] A. Author, "Title of article," Journal Name, vol. X, no. X, pp. X-X, Year.',
    ),
    CitationStyleInfo(
        id=CitationStyle.BIBTEX,
        name="BibTeX",
        description="LaTeX bibliography format for academic papers",
        example="@article{key, author={...}, title={...}, journal={...}, year={...}}",
    ),
]
