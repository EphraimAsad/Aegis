"""Create documents and document_chunks tables.

Revision ID: 002
Revises: 001
Create Date: 2026-03-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension (will fail gracefully if already enabled or not available)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Core metadata
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Publication info
        sa.Column("document_type", sa.String(length=50), nullable=False, server_default="journal-article"),
        sa.Column("publication_date", sa.String(length=20), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("journal", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True),
        # Identifiers
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("identifiers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # URLs
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.Text(), nullable=True),
        sa.Column("open_access_url", sa.Text(), nullable=True),
        # Metrics
        sa.Column("citation_count", sa.Integer(), nullable=True),
        sa.Column("reference_count", sa.Integer(), nullable=True),
        # Classification
        sa.Column("keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("subjects", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("mesh_terms", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        # Flags
        sa.Column("is_open_access", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_preprint", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_retracted", sa.Boolean(), nullable=False, server_default="false"),
        # Source tracking
        sa.Column("source_name", sa.String(length=50), nullable=True),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        # Full text
        sa.Column("full_text", sa.Text(), nullable=True),
        sa.Column("full_text_source", sa.String(length=50), nullable=True),
        # Generated content
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_findings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evidence_claims", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Processing metadata
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_doi", "documents", ["doi"], unique=True)
    op.create_index("ix_documents_year", "documents", ["year"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        # Position info
        sa.Column("start_char", sa.Integer(), nullable=True),
        sa.Column("end_char", sa.Integer(), nullable=True),
        # Section info
        sa.Column("section_type", sa.String(length=50), nullable=True),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        # Chunk metadata
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("char_count", sa.Integer(), nullable=True),
        # Embedding (stored as JSONB for now, can be migrated to vector type later)
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for chunks
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_document_index",
        "document_chunks",
        ["document_id", "chunk_index"],
        unique=True,
    )


def downgrade() -> None:
    # Drop chunks table
    op.drop_index("ix_document_chunks_document_index", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    # Drop documents table
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_year", table_name="documents")
    op.drop_index("ix_documents_doi", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_table("documents")

    # Note: We don't drop the vector extension as it might be used by other tables
