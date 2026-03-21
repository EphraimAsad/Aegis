"""Document chunking service.

Provides multiple chunking strategies for splitting documents into
smaller pieces for embedding and retrieval.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class ChunkingStrategy(StrEnum):
    """Available chunking strategies."""

    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    SECTION = "section"


@dataclass
class Chunk:
    """A text chunk with metadata."""

    content: str
    index: int
    start_char: int
    end_char: int
    section_type: str | None = None
    section_title: str | None = None
    token_count: int | None = None

    @property
    def char_count(self) -> int:
        """Return character count."""
        return len(self.content)


class BaseChunker(ABC):
    """Base class for chunking strategies."""

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        min_chunk_size: int = 100,
    ) -> None:
        """
        Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters
            overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum chunk size (smaller chunks are merged)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    @abstractmethod
    def chunk(self, text: str, section_type: str | None = None) -> list[Chunk]:
        """
        Split text into chunks.

        Args:
            text: The text to chunk
            section_type: Optional section type for all chunks

        Returns:
            List of Chunk objects
        """
        pass

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (roughly 4 chars per token for English)."""
        return len(text) // 4


class FixedSizeChunker(BaseChunker):
    """
    Fixed-size chunking with character-based splitting.

    Splits text at word boundaries to achieve approximately
    equal-sized chunks.
    """

    def chunk(self, text: str, section_type: str | None = None) -> list[Chunk]:
        """Split text into fixed-size chunks."""
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))

            # If we're not at the end, try to break at a word boundary
            if end < len(text):
                # Look for the last space within the chunk
                last_space = text.rfind(" ", start, end)
                if last_space > start + self.min_chunk_size:
                    end = last_space + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    Chunk(
                        content=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                        section_type=section_type,
                        token_count=self._estimate_tokens(chunk_text),
                    )
                )
                index += 1

            # Move start position, accounting for overlap
            if end < len(text):
                start = end - self.overlap
                if start < end - self.chunk_size:
                    start = end
            else:
                break

        return chunks


class SentenceChunker(BaseChunker):
    """
    Sentence-based chunking.

    Groups sentences together until reaching the target chunk size,
    respecting sentence boundaries.
    """

    # Sentence-ending patterns
    SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
    # More aggressive pattern including newlines
    SENTENCE_PATTERN_RELAXED = re.compile(r"(?<=[.!?])\s+|\n\n+")

    def chunk(self, text: str, section_type: str | None = None) -> list[Chunk]:
        """Split text into sentence-based chunks."""
        if not text or not text.strip():
            return []

        # Split into sentences
        sentences = self._split_sentences(text)

        chunks = []
        current_sentences: list[str] = []
        current_start = 0
        current_length = 0
        index = 0
        position = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                position += 1  # Account for whitespace
                continue

            sentence_len = len(sentence) + 1  # +1 for space

            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_len > self.chunk_size and current_sentences:
                # Create chunk from current sentences
                chunk_text = " ".join(current_sentences)
                chunks.append(
                    Chunk(
                        content=chunk_text,
                        index=index,
                        start_char=current_start,
                        end_char=current_start + len(chunk_text),
                        section_type=section_type,
                        token_count=self._estimate_tokens(chunk_text),
                    )
                )
                index += 1

                # Handle overlap by keeping some sentences
                overlap_sentences: list[str] = []
                overlap_length = 0
                for s in reversed(current_sentences):
                    if overlap_length + len(s) + 1 <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s) + 1
                    else:
                        break

                current_sentences = overlap_sentences
                current_start = (
                    position - overlap_length if overlap_length else position
                )
                current_length = overlap_length

            current_sentences.append(sentence)
            current_length += sentence_len
            position += len(sentence) + 1

        # Handle remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append(
                Chunk(
                    content=chunk_text,
                    index=index,
                    start_char=current_start,
                    end_char=current_start + len(chunk_text),
                    section_type=section_type,
                    token_count=self._estimate_tokens(chunk_text),
                )
            )

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # First try strict pattern, then relaxed if no results
        sentences = self.SENTENCE_PATTERN.split(text)
        if len(sentences) <= 1:
            sentences = self.SENTENCE_PATTERN_RELAXED.split(text)
        return [s.strip() for s in sentences if s.strip()]


class ParagraphChunker(BaseChunker):
    """
    Paragraph-based chunking.

    Splits at paragraph boundaries (double newlines) and groups
    paragraphs to reach target size.
    """

    def chunk(self, text: str, section_type: str | None = None) -> list[Chunk]:
        """Split text into paragraph-based chunks."""
        if not text or not text.strip():
            return []

        # Split into paragraphs
        paragraphs = re.split(r"\n\s*\n", text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_paragraphs: list[str] = []
        current_start = 0
        current_length = 0
        index = 0
        position = 0

        for para in paragraphs:
            para_len = len(para) + 2  # +2 for paragraph break

            # Check if adding this paragraph would exceed chunk size
            if current_length + para_len > self.chunk_size and current_paragraphs:
                # Create chunk
                chunk_text = "\n\n".join(current_paragraphs)
                chunks.append(
                    Chunk(
                        content=chunk_text,
                        index=index,
                        start_char=current_start,
                        end_char=current_start + len(chunk_text),
                        section_type=section_type,
                        token_count=self._estimate_tokens(chunk_text),
                    )
                )
                index += 1

                # For paragraphs, we don't overlap - start fresh
                current_paragraphs = []
                current_start = position
                current_length = 0

            current_paragraphs.append(para)
            current_length += para_len
            position += len(para) + 2

        # Handle remaining paragraphs
        if current_paragraphs:
            chunk_text = "\n\n".join(current_paragraphs)
            chunks.append(
                Chunk(
                    content=chunk_text,
                    index=index,
                    start_char=current_start,
                    end_char=current_start + len(chunk_text),
                    section_type=section_type,
                    token_count=self._estimate_tokens(chunk_text),
                )
            )

        return chunks


class SectionChunker(BaseChunker):
    """
    Section-based chunking for academic papers.

    Detects common academic paper sections and chunks accordingly.
    """

    # Common section headers
    SECTION_PATTERNS = [
        (r"^abstract\s*[:.]?\s*", "abstract"),
        (r"^introduction\s*[:.]?\s*", "introduction"),
        (r"^background\s*[:.]?\s*", "background"),
        (r"^related\s+work\s*[:.]?\s*", "related_work"),
        (r"^literature\s+review\s*[:.]?\s*", "literature_review"),
        (r"^methods?\s*[:.]?\s*", "methods"),
        (r"^methodology\s*[:.]?\s*", "methods"),
        (r"^materials?\s+and\s+methods?\s*[:.]?\s*", "methods"),
        (r"^experimental\s*[:.]?\s*", "methods"),
        (r"^results?\s*[:.]?\s*", "results"),
        (r"^findings?\s*[:.]?\s*", "results"),
        (r"^discussion\s*[:.]?\s*", "discussion"),
        (r"^analysis\s*[:.]?\s*", "discussion"),
        (r"^conclusion\s*[:.]?\s*", "conclusion"),
        (r"^conclusions?\s*[:.]?\s*", "conclusion"),
        (r"^summary\s*[:.]?\s*", "conclusion"),
        (r"^references?\s*[:.]?\s*", "references"),
        (r"^bibliography\s*[:.]?\s*", "references"),
        (r"^acknowledgements?\s*[:.]?\s*", "acknowledgements"),
        (r"^appendix\s*[:.]?\s*", "appendix"),
        (r"^\d+\.?\s+", "numbered_section"),
    ]

    def chunk(self, text: str, section_type: str | None = None) -> list[Chunk]:
        """Split text into section-based chunks."""
        if not text or not text.strip():
            return []

        sections = self._detect_sections(text)

        chunks = []
        index = 0
        sentence_chunker = SentenceChunker(
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            min_chunk_size=self.min_chunk_size,
        )

        for section_title, section_text, section_type_detected, start_pos in sections:
            # If section is small enough, keep as single chunk
            if len(section_text) <= self.chunk_size:
                chunks.append(
                    Chunk(
                        content=section_text,
                        index=index,
                        start_char=start_pos,
                        end_char=start_pos + len(section_text),
                        section_type=section_type_detected,
                        section_title=section_title,
                        token_count=self._estimate_tokens(section_text),
                    )
                )
                index += 1
            else:
                # Split large sections using sentence chunker
                section_chunks = sentence_chunker.chunk(
                    section_text, section_type_detected
                )
                for chunk in section_chunks:
                    chunk.index = index
                    chunk.start_char += start_pos
                    chunk.end_char += start_pos
                    chunk.section_title = section_title
                    chunks.append(chunk)
                    index += 1

        return chunks

    def _detect_sections(
        self, text: str
    ) -> list[tuple[str | None, str, str | None, int]]:
        """
        Detect sections in text.

        Returns:
            List of (section_title, section_text, section_type, start_position)
        """
        lines = text.split("\n")
        sections: list[tuple[str | None, str, str | None, int]] = []
        current_title: str | None = None
        current_type = None
        current_lines: list[str] = []
        current_start = 0
        position = 0

        for line in lines:
            stripped = line.strip()
            detected_type = None

            # Check if this line is a section header
            for pattern, sec_type in self.SECTION_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    detected_type = sec_type
                    break

            if detected_type and len(stripped) < 100:  # Headers are usually short
                # Save current section
                if current_lines:
                    section_text = "\n".join(current_lines).strip()
                    if section_text:
                        sections.append(
                            (current_title, section_text, current_type, current_start)
                        )

                # Start new section
                current_title = stripped
                current_type = detected_type
                current_lines = []
                current_start = position
            else:
                current_lines.append(line)

            position += len(line) + 1  # +1 for newline

        # Save final section
        if current_lines:
            section_text = "\n".join(current_lines).strip()
            if section_text:
                sections.append(
                    (current_title, section_text, current_type, current_start)
                )

        # If no sections detected, return entire text as single section
        if not sections:
            sections.append((None, text.strip(), None, 0))

        return sections


class ChunkingService:
    """Service for chunking documents."""

    CHUNKERS: dict[ChunkingStrategy, type[BaseChunker]] = {
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunker,
        ChunkingStrategy.SENTENCE: SentenceChunker,
        ChunkingStrategy.PARAGRAPH: ParagraphChunker,
        ChunkingStrategy.SECTION: SectionChunker,
    }

    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
        chunk_size: int = 1000,
        overlap: int = 200,
        min_chunk_size: int = 100,
    ) -> None:
        """
        Initialize chunking service.

        Args:
            strategy: Chunking strategy to use
            chunk_size: Target chunk size in characters
            overlap: Character overlap between chunks
            min_chunk_size: Minimum chunk size
        """
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

        chunker_class = self.CHUNKERS.get(strategy, SentenceChunker)
        self.chunker = chunker_class(chunk_size, overlap, min_chunk_size)

    def chunk_text(self, text: str, section_type: str | None = None) -> list[Chunk]:
        """
        Chunk text using the configured strategy.

        Args:
            text: Text to chunk
            section_type: Optional section type for all chunks

        Returns:
            List of Chunk objects
        """
        return self.chunker.chunk(text, section_type)

    def chunk_document(
        self, abstract: str | None, full_text: str | None
    ) -> list[Chunk]:
        """
        Chunk a document's content intelligently.

        Handles abstract and full text separately for better structure.

        Args:
            abstract: Document abstract
            full_text: Document full text

        Returns:
            List of Chunk objects
        """
        chunks = []
        index = 0

        # Chunk abstract first if available
        if abstract and abstract.strip():
            abstract_chunks = self.chunker.chunk(
                abstract.strip(), section_type="abstract"
            )
            for chunk in abstract_chunks:
                chunk.index = index
                chunks.append(chunk)
                index += 1

        # Then chunk full text if available
        if full_text and full_text.strip():
            # Use section chunker for full text if it's a paper
            if self.strategy == ChunkingStrategy.SECTION or len(full_text) > 5000:
                section_chunker = SectionChunker(
                    self.chunk_size, self.overlap, self.min_chunk_size
                )
                text_chunks = section_chunker.chunk(full_text.strip())
            else:
                text_chunks = self.chunker.chunk(full_text.strip())

            for chunk in text_chunks:
                chunk.index = index
                # Adjust start/end chars to account for abstract
                if abstract:
                    offset = len(abstract) + 2  # +2 for separator
                    chunk.start_char += offset
                    chunk.end_char += offset
                chunks.append(chunk)
                index += 1

        return chunks

    def estimate_chunk_count(self, text_length: int) -> int:
        """
        Estimate number of chunks for a given text length.

        Args:
            text_length: Length of text in characters

        Returns:
            Estimated chunk count
        """
        if text_length <= 0:
            return 0

        effective_chunk_size = self.chunk_size - self.overlap
        if effective_chunk_size <= 0:
            effective_chunk_size = self.chunk_size

        return max(1, (text_length + effective_chunk_size - 1) // effective_chunk_size)


def get_chunking_service(
    strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> ChunkingService:
    """
    Get a chunking service instance.

    Args:
        strategy: Chunking strategy
        chunk_size: Target chunk size
        overlap: Overlap between chunks

    Returns:
        ChunkingService instance
    """
    return ChunkingService(
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap,
    )
