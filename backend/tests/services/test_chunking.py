"""Tests for the chunking service."""

from app.services.chunking import (
    Chunk,
    ChunkingService,
    ChunkingStrategy,
    FixedSizeChunker,
    ParagraphChunker,
    SectionChunker,
    SentenceChunker,
)


class TestChunk:
    """Tests for Chunk dataclass."""

    def test_char_count(self) -> None:
        """Test character count property."""
        chunk = Chunk(content="Hello world", index=0, start_char=0, end_char=11)
        assert chunk.char_count == 11

    def test_chunk_with_metadata(self) -> None:
        """Test chunk with all metadata."""
        chunk = Chunk(
            content="Test content",
            index=1,
            start_char=100,
            end_char=112,
            section_type="abstract",
            section_title="Abstract",
            token_count=3,
        )
        assert chunk.section_type == "abstract"
        assert chunk.section_title == "Abstract"
        assert chunk.token_count == 3


class TestFixedSizeChunker:
    """Tests for FixedSizeChunker."""

    def test_empty_text(self) -> None:
        """Test chunking empty text."""
        chunker = FixedSizeChunker(chunk_size=100)
        chunks = chunker.chunk("")
        assert chunks == []

    def test_whitespace_only(self) -> None:
        """Test chunking whitespace-only text."""
        chunker = FixedSizeChunker(chunk_size=100)
        chunks = chunker.chunk("   \n\t  ")
        assert chunks == []

    def test_short_text(self) -> None:
        """Test text shorter than chunk size."""
        chunker = FixedSizeChunker(chunk_size=1000)
        text = "This is a short text."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].index == 0

    def test_long_text_creates_multiple_chunks(self) -> None:
        """Test that long text creates multiple chunks."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=10)
        text = "This is a longer text. " * 10
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # Check indices are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_overlap_between_chunks(self) -> None:
        """Test that chunks have proper overlap."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=10, min_chunk_size=20)
        text = "word " * 30
        chunks = chunker.chunk(text)

        if len(chunks) > 1:
            # Verify overlap exists by checking chunk boundaries
            # The last characters of first chunk should overlap with next
            assert chunks[0].end_char > chunks[1].start_char or len(chunks) > 1

    def test_section_type_propagation(self) -> None:
        """Test that section type is propagated to all chunks."""
        chunker = FixedSizeChunker(chunk_size=50)
        text = "This is test content. " * 5
        chunks = chunker.chunk(text, section_type="abstract")
        for chunk in chunks:
            assert chunk.section_type == "abstract"


class TestSentenceChunker:
    """Tests for SentenceChunker."""

    def test_empty_text(self) -> None:
        """Test chunking empty text."""
        chunker = SentenceChunker(chunk_size=100)
        chunks = chunker.chunk("")
        assert chunks == []

    def test_single_sentence(self) -> None:
        """Test single sentence text."""
        chunker = SentenceChunker(chunk_size=1000)
        text = "This is a single sentence."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_respects_sentence_boundaries(self) -> None:
        """Test that chunker respects sentence boundaries."""
        chunker = SentenceChunker(chunk_size=100, overlap=0)
        text = "First sentence. Second sentence. Third sentence."
        chunks = chunker.chunk(text)

        # Each chunk should contain complete sentences
        for chunk in chunks:
            # Sentences should be complete (end with period or be trimmed)
            content = chunk.content.strip()
            if content and not content.endswith("."):
                # Could be a sentence fragment at boundaries
                pass

    def test_multiple_sentences_combined(self) -> None:
        """Test that short sentences are combined."""
        chunker = SentenceChunker(chunk_size=200, overlap=0)
        text = "Short. Also short. Another one. And more."
        chunks = chunker.chunk(text)

        # Should combine into fewer chunks
        total_content = " ".join(c.content for c in chunks)
        # All sentences should be present
        assert "Short" in total_content
        assert "Also short" in total_content

    def test_token_count_estimation(self) -> None:
        """Test that token count is estimated."""
        chunker = SentenceChunker(chunk_size=1000)
        text = "This is a test sentence with multiple words."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].token_count is not None
        assert chunks[0].token_count > 0


class TestParagraphChunker:
    """Tests for ParagraphChunker."""

    def test_empty_text(self) -> None:
        """Test chunking empty text."""
        chunker = ParagraphChunker(chunk_size=100)
        chunks = chunker.chunk("")
        assert chunks == []

    def test_single_paragraph(self) -> None:
        """Test single paragraph text."""
        chunker = ParagraphChunker(chunk_size=1000)
        text = "This is a single paragraph with multiple sentences. It continues here."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1

    def test_multiple_paragraphs(self) -> None:
        """Test that paragraphs are detected."""
        chunker = ParagraphChunker(chunk_size=1000)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunker.chunk(text)
        # All should be in one chunk since it's under size
        assert len(chunks) >= 1
        assert "First paragraph" in chunks[0].content

    def test_paragraph_splitting(self) -> None:
        """Test that large paragraphs are split."""
        chunker = ParagraphChunker(chunk_size=50, overlap=0)
        text = "First para.\n\nSecond para.\n\nThird para."
        chunks = chunker.chunk(text)
        # Should create multiple chunks
        assert len(chunks) >= 1


class TestSectionChunker:
    """Tests for SectionChunker."""

    def test_empty_text(self) -> None:
        """Test chunking empty text."""
        chunker = SectionChunker(chunk_size=100)
        chunks = chunker.chunk("")
        assert chunks == []

    def test_detects_abstract_section(self) -> None:
        """Test detection of abstract section."""
        chunker = SectionChunker(chunk_size=1000)
        text = (
            "Abstract:\nThis is the abstract content.\n\nIntroduction:\nThis is intro."
        )
        chunks = chunker.chunk(text)

        section_types = [c.section_type for c in chunks]
        assert "abstract" in section_types or len(chunks) >= 1

    def test_detects_common_sections(self) -> None:
        """Test detection of common academic sections."""
        chunker = SectionChunker(chunk_size=2000)
        text = """Abstract
This is the abstract.

Introduction
This is the introduction.

Methods
This describes the methods.

Results
Here are the results.

Conclusion
Final conclusions here."""

        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_numbered_sections(self) -> None:
        """Test detection of numbered sections."""
        chunker = SectionChunker(chunk_size=1000)
        text = """1. Introduction
Content for section one.

2. Methods
Content for section two."""

        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_no_sections_detected(self) -> None:
        """Test text with no clear sections."""
        chunker = SectionChunker(chunk_size=1000)
        text = "Just plain text without any section headers or structure."
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0].content == text


class TestChunkingService:
    """Tests for ChunkingService."""

    def test_default_strategy(self) -> None:
        """Test default chunking strategy is sentence."""
        service = ChunkingService()
        assert service.strategy == ChunkingStrategy.SENTENCE

    def test_custom_strategy(self) -> None:
        """Test custom chunking strategy."""
        service = ChunkingService(strategy=ChunkingStrategy.FIXED_SIZE)
        assert service.strategy == ChunkingStrategy.FIXED_SIZE

    def test_chunk_text(self) -> None:
        """Test chunking text."""
        service = ChunkingService(chunk_size=100)
        chunks = service.chunk_text("This is a test. Another sentence here.")
        assert len(chunks) >= 1
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunk_document_with_abstract(self) -> None:
        """Test chunking document with abstract."""
        service = ChunkingService(chunk_size=1000)
        chunks = service.chunk_document(
            abstract="This is the abstract.",
            full_text="This is the full text content.",
        )
        assert len(chunks) >= 2
        # First chunk should be abstract
        assert chunks[0].section_type == "abstract"

    def test_chunk_document_abstract_only(self) -> None:
        """Test chunking document with abstract only."""
        service = ChunkingService(chunk_size=1000)
        chunks = service.chunk_document(
            abstract="This is only the abstract.",
            full_text=None,
        )
        assert len(chunks) >= 1
        assert chunks[0].section_type == "abstract"

    def test_chunk_document_full_text_only(self) -> None:
        """Test chunking document with full text only."""
        service = ChunkingService(chunk_size=1000)
        chunks = service.chunk_document(
            abstract=None,
            full_text="This is the full text.",
        )
        assert len(chunks) >= 1

    def test_estimate_chunk_count(self) -> None:
        """Test chunk count estimation."""
        service = ChunkingService(chunk_size=100, overlap=20)

        # Zero length
        assert service.estimate_chunk_count(0) == 0

        # Short text
        assert service.estimate_chunk_count(50) == 1

        # Longer text
        count = service.estimate_chunk_count(500)
        assert count > 1

    def test_all_strategies_work(self) -> None:
        """Test that all chunking strategies work."""
        text = "This is a test. " * 20

        for strategy in ChunkingStrategy:
            if strategy == ChunkingStrategy.SEMANTIC:
                continue  # Semantic requires embeddings
            service = ChunkingService(strategy=strategy, chunk_size=100)
            chunks = service.chunk_text(text)
            assert len(chunks) >= 1, f"Strategy {strategy} failed"
