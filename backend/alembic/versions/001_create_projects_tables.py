"""Create projects and clarification_questions tables.

Revision ID: 001
Revises:
Create Date: 2026-03-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("max_results_per_source", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "sources_enabled",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default='["openalex", "crossref", "semantic_scholar", "arxiv", "pubmed"]',
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index on status for filtering
    op.create_index("ix_projects_status", "projects", ["status"])

    # Create clarification_questions table
    op.create_table(
        "clarification_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="scope"),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("scope_field", sa.String(length=100), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("answer_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index on project_id for faster lookups
    op.create_index("ix_clarification_questions_project_id", "clarification_questions", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_clarification_questions_project_id", table_name="clarification_questions")
    op.drop_table("clarification_questions")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")
