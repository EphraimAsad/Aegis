"""Vector retrieval service.

Provides semantic search using document embeddings and pgvector.
"""

import json
import math
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.embedding import EmbeddingService


@dataclass
class RetrievalResult:
    """A single retrieval result."""

    chunk_id: int
    document_id: int
    document_title: str
    content: str
    section_type: str | None
    section_title: str | None
    similarity_score: float
    chunk_index: int


@dataclass
class RetrievalResponse:
    """Response from retrieval query."""

    query: str
    results: list[RetrievalResult]
    total_results: int
    model: str | None = None


class RetrievalService:
    """Service for vector-based document retrieval."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """
        Initialize retrieval service.

        Args:
            db: Database session
            embedding_service: Service for generating query embeddings
        """
        self.db = db
        self._embedding_service = embedding_service

    async def _get_embedding_service(self) -> EmbeddingService:
        """Get or create embedding service."""
        if self._embedding_service is None:
            from app.services.embedding import get_embedding_service

            self._embedding_service = get_embedding_service(self.db)
        return self._embedding_service

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def search(
        self,
        query: str,
        project_id: int | None = None,
        document_ids: list[int] | None = None,
        top_k: int = 10,
        min_similarity: float = 0.5,
        section_types: list[str] | None = None,
    ) -> RetrievalResponse:
        """
        Perform semantic search across document chunks.

        Args:
            query: Search query text
            project_id: Optional project filter
            document_ids: Optional document filter
            top_k: Maximum results to return
            min_similarity: Minimum similarity threshold
            section_types: Filter by section types

        Returns:
            RetrievalResponse with matching chunks
        """
        # Generate query embedding
        embedding_service = await self._get_embedding_service()
        query_embedding, model = await embedding_service.embed_text(query)

        # Build query for chunks with embeddings
        # Note: This uses a JSON-based approach for compatibility
        # In production with pgvector, use the vector type and operators

        chunk_query = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.content,
                DocumentChunk.section_type,
                DocumentChunk.section_title,
                DocumentChunk.chunk_index,
                DocumentChunk.embedding,
                Document.title.label("document_title"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.isnot(None))
            .where(Document.status == DocumentStatus.READY)
        )

        if project_id is not None:
            chunk_query = chunk_query.where(Document.project_id == project_id)

        if document_ids:
            chunk_query = chunk_query.where(Document.id.in_(document_ids))

        if section_types:
            chunk_query = chunk_query.where(
                DocumentChunk.section_type.in_(section_types)
            )

        result = await self.db.execute(chunk_query)
        rows = result.fetchall()

        # Calculate similarities
        scored_results = []
        for row in rows:
            chunk_embedding = row.embedding
            if isinstance(chunk_embedding, str):
                chunk_embedding = json.loads(chunk_embedding)

            similarity = self._cosine_similarity(query_embedding, chunk_embedding)

            if similarity >= min_similarity:
                scored_results.append(
                    RetrievalResult(
                        chunk_id=row.id,
                        document_id=row.document_id,
                        document_title=row.document_title,
                        content=row.content,
                        section_type=row.section_type,
                        section_title=row.section_title,
                        similarity_score=round(similarity, 4),
                        chunk_index=row.chunk_index,
                    )
                )

        # Sort by similarity and limit
        scored_results.sort(key=lambda x: x.similarity_score, reverse=True)
        top_results = scored_results[:top_k]

        return RetrievalResponse(
            query=query,
            results=top_results,
            total_results=len(scored_results),
            model=model,
        )

    async def search_with_pgvector(
        self,
        query: str,
        project_id: int | None = None,
        top_k: int = 10,
        min_similarity: float = 0.5,
    ) -> RetrievalResponse:
        """
        Perform semantic search using pgvector operators.

        This method requires pgvector extension and vector column type.
        Falls back to regular search if pgvector is not available.

        Args:
            query: Search query text
            project_id: Optional project filter
            top_k: Maximum results to return
            min_similarity: Minimum similarity threshold

        Returns:
            RetrievalResponse with matching chunks
        """
        try:
            # Try pgvector-based search
            embedding_service = await self._get_embedding_service()
            query_embedding, model = await embedding_service.embed_text(query)

            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Build pgvector query using cosine similarity
            sql = text("""
                SELECT
                    c.id,
                    c.document_id,
                    c.content,
                    c.section_type,
                    c.section_title,
                    c.chunk_index,
                    d.title as document_title,
                    1 - (c.embedding_vector <=> :embedding::vector) as similarity
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.embedding_vector IS NOT NULL
                AND d.status = 'ready'
                AND (:project_id IS NULL OR d.project_id = :project_id)
                AND 1 - (c.embedding_vector <=> :embedding::vector) >= :min_similarity
                ORDER BY c.embedding_vector <=> :embedding::vector
                LIMIT :top_k
            """)

            result = await self.db.execute(
                sql,
                {
                    "embedding": embedding_str,
                    "project_id": project_id,
                    "min_similarity": min_similarity,
                    "top_k": top_k,
                },
            )

            rows = result.fetchall()
            results = [
                RetrievalResult(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    document_title=row.document_title,
                    content=row.content,
                    section_type=row.section_type,
                    section_title=row.section_title,
                    similarity_score=round(float(row.similarity), 4),
                    chunk_index=row.chunk_index,
                )
                for row in rows
            ]

            return RetrievalResponse(
                query=query,
                results=results,
                total_results=len(results),
                model=model,
            )

        except Exception:
            # Fall back to JSON-based similarity
            return await self.search(
                query=query,
                project_id=project_id,
                top_k=top_k,
                min_similarity=min_similarity,
            )

    async def find_similar_chunks(
        self,
        chunk_id: int,
        top_k: int = 10,
        exclude_same_document: bool = True,
    ) -> list[RetrievalResult]:
        """
        Find chunks similar to a given chunk.

        Args:
            chunk_id: Source chunk ID
            top_k: Maximum results
            exclude_same_document: Whether to exclude chunks from same document

        Returns:
            List of similar chunks
        """
        # Get source chunk
        source_result = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )
        source_chunk = source_result.scalar_one_or_none()

        if not source_chunk or not source_chunk.embedding:
            return []

        source_embedding = source_chunk.embedding
        if isinstance(source_embedding, str):
            source_embedding = json.loads(source_embedding)

        # Query for other chunks
        query = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.content,
                DocumentChunk.section_type,
                DocumentChunk.section_title,
                DocumentChunk.chunk_index,
                DocumentChunk.embedding,
                Document.title.label("document_title"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.isnot(None))
            .where(DocumentChunk.id != chunk_id)
            .where(Document.status == DocumentStatus.READY)
        )

        if exclude_same_document:
            query = query.where(DocumentChunk.document_id != source_chunk.document_id)

        result = await self.db.execute(query)
        rows = result.fetchall()

        # Calculate similarities
        scored_results = []
        for row in rows:
            chunk_embedding = row.embedding
            if isinstance(chunk_embedding, str):
                chunk_embedding = json.loads(chunk_embedding)

            similarity = self._cosine_similarity(source_embedding, chunk_embedding)

            scored_results.append(
                RetrievalResult(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    document_title=row.document_title,
                    content=row.content,
                    section_type=row.section_type,
                    section_title=row.section_title,
                    similarity_score=round(similarity, 4),
                    chunk_index=row.chunk_index,
                )
            )

        # Sort and limit
        scored_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored_results[:top_k]

    async def find_related_documents(
        self,
        document_id: int,
        project_id: int | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Find documents related to a given document.

        Args:
            document_id: Source document ID
            project_id: Optional project filter
            top_k: Maximum results

        Returns:
            List of related documents with scores
        """
        # Get all chunks from source document
        source_result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .where(DocumentChunk.embedding.isnot(None))
        )
        source_chunks = list(source_result.scalars().all())

        if not source_chunks:
            return []

        # Build query for chunks from other documents
        query = (
            select(
                DocumentChunk.document_id,
                DocumentChunk.embedding,
                Document.title,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.embedding.isnot(None))
            .where(DocumentChunk.document_id != document_id)
            .where(Document.status == DocumentStatus.READY)
        )

        if project_id is not None:
            query = query.where(Document.project_id == project_id)

        result = await self.db.execute(query)
        rows = result.fetchall()

        # Calculate average similarity per document
        doc_scores: dict[int, dict] = {}
        for row in rows:
            other_embedding = row.embedding
            if isinstance(other_embedding, str):
                other_embedding = json.loads(other_embedding)

            # Calculate max similarity to any source chunk
            max_sim = 0.0
            for source_chunk in source_chunks:
                source_emb = source_chunk.embedding
                if isinstance(source_emb, str):
                    source_emb = json.loads(source_emb)
                sim = self._cosine_similarity(source_emb, other_embedding)  # type: ignore[arg-type]
                max_sim = max(max_sim, sim)

            doc_id = row.document_id
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    "document_id": doc_id,
                    "title": row.title,
                    "max_similarity": max_sim,
                    "chunk_count": 1,
                    "total_similarity": max_sim,
                }
            else:
                doc_scores[doc_id]["chunk_count"] += 1
                doc_scores[doc_id]["total_similarity"] += max_sim
                doc_scores[doc_id]["max_similarity"] = max(
                    doc_scores[doc_id]["max_similarity"], max_sim
                )

        # Calculate average and sort
        for doc in doc_scores.values():
            doc["avg_similarity"] = doc["total_similarity"] / doc["chunk_count"]
            doc["score"] = (doc["max_similarity"] + doc["avg_similarity"]) / 2

        sorted_docs = sorted(
            doc_scores.values(), key=lambda x: x["score"], reverse=True
        )

        return [
            {
                "document_id": doc["document_id"],
                "title": doc["title"],
                "similarity_score": round(doc["score"], 4),
            }
            for doc in sorted_docs[:top_k]
        ]

    async def get_retrieval_stats(
        self,
        project_id: int | None = None,
    ) -> dict:
        """
        Get statistics about retrievable content.

        Args:
            project_id: Optional project filter

        Returns:
            Dict with retrieval statistics
        """
        base_query = select(
            func.count(DocumentChunk.id).label("total_chunks"),
            func.count(DocumentChunk.embedding).label("embedded_chunks"),
        ).join(Document, Document.id == DocumentChunk.document_id)

        if project_id is not None:
            base_query = base_query.where(Document.project_id == project_id)

        result = await self.db.execute(base_query)
        row = result.fetchone()

        doc_query = select(func.count(Document.id)).where(
            Document.status == DocumentStatus.READY
        )
        if project_id is not None:
            doc_query = doc_query.where(Document.project_id == project_id)

        doc_result = await self.db.execute(doc_query)
        doc_count = doc_result.scalar() or 0

        return {
            "total_chunks": row.total_chunks if row else 0,
            "embedded_chunks": row.embedded_chunks if row else 0,
            "ready_documents": doc_count,
            "coverage": (
                round(row.embedded_chunks / row.total_chunks * 100, 1)
                if row and row.total_chunks > 0
                else 0
            ),
        }


def get_retrieval_service(
    db: AsyncSession,
    embedding_service: EmbeddingService | None = None,
) -> RetrievalService:
    """
    Get a retrieval service instance.

    Args:
        db: Database session
        embedding_service: Optional embedding service

    Returns:
        RetrievalService instance
    """
    return RetrievalService(db=db, embedding_service=embedding_service)
