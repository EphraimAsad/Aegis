"""Embedding generation service.

Uses the provider abstraction to generate embeddings for document chunks.
Supports batch processing and caching.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentChunk, DocumentStatus
from app.providers import get_provider_manager
from app.providers.base import BaseProvider
from app.services.chunking import ChunkingService, ChunkingStrategy


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    chunk_id: int
    embedding: list[float]
    model: str
    dimension: int


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding generation."""

    successful: list[EmbeddingResult]
    failed: list[tuple[int, str]]  # (chunk_id, error_message)
    total_tokens: int


class EmbeddingService:
    """Service for generating embeddings."""

    # Batch size limits
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 500

    def __init__(
        self,
        db: AsyncSession,
        provider_name: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """
        Initialize embedding service.

        Args:
            db: Database session
            provider_name: Provider to use for embeddings (None = default)
            model_name: Model to use for embeddings (None = provider default)
        """
        self.db = db
        self._provider_name = provider_name
        self._model_name = model_name
        self._provider: BaseProvider | None = None

    async def _get_provider(self) -> BaseProvider:
        """Get or initialize the embedding provider."""
        if self._provider is None:
            manager = get_provider_manager()
            if self._provider_name:
                self._provider = manager.get(self._provider_name)
            else:
                self._provider = manager.get_default()

            if not self._provider:
                raise RuntimeError("No embedding provider available")

        return self._provider

    async def embed_text(self, text: str) -> tuple[list[float], str]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Tuple of (embedding vector, model name)
        """
        provider = await self._get_provider()
        response = await provider.embed(
            texts=[text],
            model=self._model_name,
        )
        return response.embeddings[0], response.model

    async def embed_texts(
        self,
        texts: list[str],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> tuple[list[list[float]], str]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per batch

        Returns:
            Tuple of (list of embedding vectors, model name)
        """
        if not texts:
            return [], ""

        provider = await self._get_provider()
        all_embeddings: list[list[float]] = []
        model_name = ""

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await provider.embed(
                texts=batch,
                model=self._model_name,
            )
            all_embeddings.extend(response.embeddings)
            model_name = response.model

        return all_embeddings, model_name

    async def embed_chunks(
        self,
        chunks: Sequence[DocumentChunk],
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: Chunks to embed
            batch_size: Number of chunks per batch

        Returns:
            BatchEmbeddingResult with successful and failed embeddings
        """
        if not chunks:
            return BatchEmbeddingResult(successful=[], failed=[], total_tokens=0)

        provider = await self._get_provider()
        successful: list[EmbeddingResult] = []
        failed: list[tuple[int, str]] = []
        total_tokens = 0

        # Process in batches
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [chunk.content for chunk in batch]

            try:
                response = await provider.embed(
                    texts=texts,
                    model=self._model_name,
                )

                # Store results
                for chunk, embedding in zip(batch, response.embeddings, strict=False):
                    successful.append(
                        EmbeddingResult(
                            chunk_id=chunk.id,
                            embedding=embedding,
                            model=response.model,
                            dimension=len(embedding),
                        )
                    )

                total_tokens += response.total_tokens  # type: ignore[attr-defined]

            except Exception as e:
                # Mark all chunks in failed batch
                for chunk in batch:
                    failed.append((chunk.id, str(e)))

        return BatchEmbeddingResult(
            successful=successful,
            failed=failed,
            total_tokens=total_tokens,
        )

    async def process_document(
        self,
        document_id: int,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> dict:
        """
        Process a document: chunk and generate embeddings.

        Args:
            document_id: Document ID to process
            chunking_strategy: How to chunk the text
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            batch_size: Embedding batch size

        Returns:
            Processing result with statistics
        """
        from app.services.document import DocumentService

        doc_service = DocumentService(self.db)
        document = await doc_service.get(document_id)

        # Update status
        await doc_service.update_status(document_id, DocumentStatus.PROCESSING)

        try:
            # Initialize chunking service
            chunking_service = ChunkingService(
                strategy=chunking_strategy,
                chunk_size=chunk_size,
                overlap=chunk_overlap,
            )

            # Chunk document
            chunks = chunking_service.chunk_document(
                abstract=document.abstract,
                full_text=document.full_text,
            )

            if not chunks:
                # No content to process
                await doc_service.update_status(document_id, DocumentStatus.READY)
                return {
                    "document_id": document_id,
                    "chunks_created": 0,
                    "embeddings_generated": 0,
                    "status": "ready",
                }

            # Create chunk records in database
            db_chunks = []
            for chunk in chunks:
                db_chunk = await doc_service.add_chunk(
                    document_id=document_id,
                    content=chunk.content,
                    chunk_index=chunk.index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    section_type=chunk.section_type,
                    section_title=chunk.section_title,
                    token_count=chunk.token_count,
                )
                db_chunks.append(db_chunk)

            await self.db.commit()

            # Generate embeddings
            embedding_result = await self.embed_chunks(db_chunks, batch_size)

            # Store embeddings
            for result in embedding_result.successful:
                await doc_service.update_chunk_embedding(
                    chunk_id=result.chunk_id,
                    embedding=result.embedding,
                    model=result.model,
                )

            # Update document
            document.embedding_model = (
                embedding_result.successful[0].model
                if embedding_result.successful
                else None
            )

            if embedding_result.failed:
                document.status = DocumentStatus.ERROR
                document.error_message = (
                    f"Failed to embed {len(embedding_result.failed)} chunks"
                )
            else:
                document.status = DocumentStatus.READY

            await self.db.commit()

            status_value = document.status.value if hasattr(document.status, 'value') else document.status
            return {
                "document_id": document_id,
                "chunks_created": len(db_chunks),
                "embeddings_generated": len(embedding_result.successful),
                "embeddings_failed": len(embedding_result.failed),
                "total_tokens": embedding_result.total_tokens,
                "status": status_value,
                "error": document.error_message,
            }

        except Exception as e:
            await doc_service.update_status(
                document_id,
                DocumentStatus.ERROR,
                error_message=str(e),
            )
            await self.db.commit()
            raise

    async def process_documents(
        self,
        document_ids: list[int],
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_concurrent: int = 5,
    ) -> list[dict]:
        """
        Process multiple documents concurrently.

        Args:
            document_ids: Document IDs to process
            chunking_strategy: How to chunk the text
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            batch_size: Embedding batch size
            max_concurrent: Maximum concurrent documents

        Returns:
            List of processing results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_one(doc_id: int) -> dict:
            async with semaphore:
                try:
                    return await self.process_document(
                        document_id=doc_id,
                        chunking_strategy=chunking_strategy,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        batch_size=batch_size,
                    )
                except Exception as e:
                    return {
                        "document_id": doc_id,
                        "status": "error",
                        "error": str(e),
                    }

        tasks = [process_one(doc_id) for doc_id in document_ids]
        results = await asyncio.gather(*tasks)

        return list(results)

    async def reembed_document(
        self,
        document_id: int,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> dict:
        """
        Re-generate embeddings for an existing document's chunks.

        Useful when changing embedding models.

        Args:
            document_id: Document ID
            batch_size: Embedding batch size

        Returns:
            Processing result
        """
        from app.services.document import DocumentService

        doc_service = DocumentService(self.db)
        chunks = await doc_service.get_chunks(document_id)

        if not chunks:
            return {
                "document_id": document_id,
                "embeddings_updated": 0,
                "status": "no_chunks",
            }

        # Generate new embeddings
        embedding_result = await self.embed_chunks(chunks, batch_size)

        # Update embeddings
        for result in embedding_result.successful:
            await doc_service.update_chunk_embedding(
                chunk_id=result.chunk_id,
                embedding=result.embedding,
                model=result.model,
            )

        # Update document embedding model
        document = await doc_service.get(document_id)
        if embedding_result.successful:
            document.embedding_model = embedding_result.successful[0].model

        await self.db.commit()

        return {
            "document_id": document_id,
            "embeddings_updated": len(embedding_result.successful),
            "embeddings_failed": len(embedding_result.failed),
            "total_tokens": embedding_result.total_tokens,
            "model": document.embedding_model,
        }


def get_embedding_service(
    db: AsyncSession,
    provider_name: str | None = None,
    model_name: str | None = None,
) -> EmbeddingService:
    """
    Get an embedding service instance.

    Args:
        db: Database session
        provider_name: Provider name (None = default)
        model_name: Model name (None = provider default)

    Returns:
        EmbeddingService instance
    """
    return EmbeddingService(
        db=db,
        provider_name=provider_name,
        model_name=model_name,
    )
