"""Document service for business logic."""

import builtins

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.schemas.paper import Paper


class DocumentService:
    """Service for document operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    async def create(self, request: DocumentCreate) -> Document:
        """
        Create a new document.

        Args:
            request: Document creation request

        Returns:
            The created document
        """
        document = Document(
            project_id=request.project_id,
            title=request.title,
            abstract=request.abstract,
            authors=(
                [a.model_dump() for a in request.authors] if request.authors else []
            ),
            document_type=(
                request.document_type.value
                if request.document_type
                else "journal-article"
            ),
            publication_date=request.publication_date,
            year=request.year,
            journal=request.journal.model_dump() if request.journal else None,
            language=request.language,
            doi=request.doi,
            identifiers=(
                [i.model_dump() for i in request.identifiers]
                if request.identifiers
                else []
            ),
            url=request.url,
            pdf_url=request.pdf_url,
            open_access_url=request.open_access_url,
            citation_count=request.citation_count,
            reference_count=request.reference_count,
            keywords=request.keywords,
            subjects=request.subjects,
            mesh_terms=request.mesh_terms,
            tags=request.tags,
            is_open_access=request.is_open_access,
            is_preprint=request.is_preprint,
            is_retracted=request.is_retracted,
            source_name=request.source_name,
            source_id=request.source_id,
            source_url=request.source_url,
            status=DocumentStatus.PENDING,
        )

        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def create_from_paper(
        self, project_id: int, paper: Paper, tags: list[str] | None = None
    ) -> Document:
        """
        Create a document from a Paper schema (from search results).

        Args:
            project_id: The project to add the document to
            paper: The Paper object from search
            tags: Optional initial tags

        Returns:
            The created document
        """
        # Check for duplicate by DOI
        if paper.doi:
            existing = await self.get_by_doi(paper.doi, project_id)
            if existing:
                raise ValidationError(
                    f"Document with DOI {paper.doi} already exists in project",
                    details={"existing_id": existing.id, "doi": paper.doi},
                )

        document = Document(
            project_id=project_id,
            title=paper.title,
            abstract=paper.abstract,
            authors=[a.model_dump() for a in paper.authors],
            document_type=paper.document_type.value,
            publication_date=(
                paper.publication_date.isoformat() if paper.publication_date else None
            ),
            year=paper.year,
            journal=paper.journal.model_dump() if paper.journal else None,
            language=paper.language,
            doi=paper.doi,
            identifiers=[i.model_dump() for i in paper.identifiers],
            url=str(paper.url) if paper.url else None,
            pdf_url=str(paper.pdf_url) if paper.pdf_url else None,
            open_access_url=(
                str(paper.open_access_url) if paper.open_access_url else None
            ),
            citation_count=paper.citation_count,
            reference_count=paper.reference_count,
            keywords=paper.keywords,
            subjects=paper.subjects,
            mesh_terms=paper.mesh_terms,
            tags=tags or [],
            is_open_access=paper.is_open_access,
            is_preprint=paper.is_preprint,
            is_retracted=paper.is_retracted,
            source_name=paper.primary_source,
            source_id=paper.sources[0].id if paper.sources else None,
            source_url=(
                str(paper.sources[0].url)
                if paper.sources and paper.sources[0].url
                else None
            ),
            status=DocumentStatus.PENDING,
        )

        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def get(self, document_id: int) -> Document:
        """
        Get a document by ID.

        Args:
            document_id: The document ID

        Returns:
            The document

        Raises:
            NotFoundError: If document not found
        """
        result = await self.db.execute(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundError(
                f"Document with id {document_id} not found",
                details={"document_id": document_id},
            )

        return document

    async def get_by_doi(
        self, doi: str, project_id: int | None = None
    ) -> Document | None:
        """
        Get a document by DOI, optionally within a project.

        Args:
            doi: The DOI
            project_id: Optional project ID filter

        Returns:
            The document or None if not found
        """
        query = select(Document).where(Document.doi == doi)
        if project_id:
            query = query.where(Document.project_id == project_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        project_id: int,
        page: int = 1,
        page_size: int = 20,
        status: DocumentStatus | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[Document], int]:
        """
        List documents for a project with pagination.

        Args:
            project_id: The project ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            tags: Filter by tags (any match)

        Returns:
            Tuple of (documents, total_count)
        """
        query = select(Document).where(Document.project_id == project_id)

        if status:
            query = query.where(Document.status == status)

        if tags:
            # Filter documents that have any of the specified tags
            query = query.where(Document.tags.overlap(tags))

        # Count total
        count_query = select(func.count(Document.id)).where(
            Document.project_id == project_id
        )
        if status:
            count_query = count_query.where(Document.status == status)
        if tags:
            count_query = count_query.where(Document.tags.overlap(tags))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Document.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        documents = list(result.scalars().all())

        return documents, total

    async def update(self, document_id: int, request: DocumentUpdate) -> Document:
        """
        Update a document.

        Args:
            document_id: The document ID
            request: Update request

        Returns:
            The updated document
        """
        document = await self.get(document_id)

        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(document, field, value)

        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def update_status(
        self, document_id: int, status: DocumentStatus, error_message: str | None = None
    ) -> Document:
        """
        Update document processing status.

        Args:
            document_id: The document ID
            status: New status
            error_message: Optional error message if status is ERROR

        Returns:
            The updated document
        """
        document = await self.get(document_id)
        document.status = status
        if error_message:
            document.error_message = error_message

        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def delete(self, document_id: int) -> None:
        """
        Delete a document.

        Args:
            document_id: The document ID
        """
        document = await self.get(document_id)
        await self.db.delete(document)
        await self.db.flush()

    async def add_chunk(
        self,
        document_id: int,
        content: str,
        chunk_index: int,
        start_char: int | None = None,
        end_char: int | None = None,
        section_type: str | None = None,
        section_title: str | None = None,
        token_count: int | None = None,
    ) -> DocumentChunk:
        """
        Add a chunk to a document.

        Args:
            document_id: The document ID
            content: Chunk text content
            chunk_index: Index of this chunk
            start_char: Starting character position
            end_char: Ending character position
            section_type: Type of section (abstract, intro, etc.)
            section_title: Title of the section
            token_count: Number of tokens in chunk

        Returns:
            The created chunk
        """
        chunk = DocumentChunk(
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            section_type=section_type,
            section_title=section_title,
            token_count=token_count,
            char_count=len(content),
        )

        self.db.add(chunk)
        await self.db.flush()
        await self.db.refresh(chunk)

        # Update chunk count on document
        await self.db.execute(select(Document).where(Document.id == document_id))
        result = await self.db.execute(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document_id
            )
        )
        count = result.scalar() or 0

        await self.db.execute(
            Document.__table__.update()  # type: ignore[attr-defined]
            .where(Document.id == document_id)
            .values(chunk_count=count)
        )

        return chunk

    async def get_chunks(self, document_id: int) -> builtins.list[DocumentChunk]:
        """
        Get all chunks for a document.

        Args:
            document_id: The document ID

        Returns:
            List of chunks ordered by index
        """
        result = await self.db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def update_chunk_embedding(
        self,
        chunk_id: int,
        embedding: builtins.list[float],
        model: str,
    ) -> DocumentChunk:
        """
        Update a chunk's embedding.

        Args:
            chunk_id: The chunk ID
            embedding: The embedding vector
            model: The embedding model used

        Returns:
            The updated chunk
        """
        result = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.id == chunk_id)
        )
        chunk = result.scalar_one_or_none()

        if not chunk:
            raise NotFoundError(
                f"Chunk with id {chunk_id} not found",
                details={"chunk_id": chunk_id},
            )

        chunk.embedding = embedding
        chunk.embedding_model = model
        chunk.embedding_dimension = len(embedding)

        await self.db.flush()
        await self.db.refresh(chunk)

        return chunk

    async def set_summary(self, document_id: int, summary: str) -> Document:
        """
        Set the summary for a document.

        Args:
            document_id: The document ID
            summary: The generated summary

        Returns:
            The updated document
        """
        document = await self.get(document_id)
        document.summary = summary

        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def set_evidence_claims(
        self, document_id: int, claims: builtins.list[dict]
    ) -> Document:
        """
        Set the evidence claims for a document.

        Args:
            document_id: The document ID
            claims: List of evidence claim objects

        Returns:
            The updated document
        """
        document = await self.get(document_id)
        document.evidence_claims = claims

        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def set_key_findings(
        self, document_id: int, findings: builtins.list[dict]
    ) -> Document:
        """
        Set the key findings for a document.

        Args:
            document_id: The document ID
            findings: List of finding objects

        Returns:
            The updated document
        """
        document = await self.get(document_id)
        document.key_findings = findings

        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def set_full_text(
        self, document_id: int, full_text: str, source: str
    ) -> Document:
        """
        Set the full text for a document.

        Args:
            document_id: The document ID
            full_text: The full text content
            source: The source of the full text

        Returns:
            The updated document
        """
        document = await self.get(document_id)
        document.full_text = full_text
        document.full_text_source = source

        await self.db.flush()
        await self.db.refresh(document)

        return document

    async def count_by_project(self, project_id: int) -> dict:
        """
        Get document counts by status for a project.

        Args:
            project_id: The project ID

        Returns:
            Dict of status -> count
        """
        result = await self.db.execute(
            select(Document.status, func.count(Document.id))
            .where(Document.project_id == project_id)
            .group_by(Document.status)
        )
        counts = {row[0]: row[1] for row in result.all()}

        return {
            "pending": counts.get(DocumentStatus.PENDING, 0),
            "downloading": counts.get(DocumentStatus.DOWNLOADING, 0),
            "processing": counts.get(DocumentStatus.PROCESSING, 0),
            "ready": counts.get(DocumentStatus.READY, 0),
            "error": counts.get(DocumentStatus.ERROR, 0),
            "total": sum(counts.values()),
        }
