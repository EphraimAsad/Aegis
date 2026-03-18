"""Create jobs table.

Revision ID: 003
Revises: 002
Create Date: 2026-03-17

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Job identification
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("job_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Status
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        # Progress
        sa.Column("progress", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_steps", sa.Integer(), nullable=False, server_default="1"),
        # Timing
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_completion", sa.DateTime(timezone=True), nullable=True),
        # Input/Output
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        # Statistics
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default="0"),
        # Resource tracking
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("api_calls_made", sa.Integer(), nullable=False, server_default="0"),
        # Relationships
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("parent_job_id", sa.Integer(), nullable=True),
        # Retry tracking
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
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
        # Constraints
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("ix_jobs_celery_task_id", "jobs", ["celery_task_id"], unique=True)
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
    op.create_index("ix_jobs_parent_job_id", "jobs", ["parent_job_id"])
    op.create_index("ix_jobs_job_type", "jobs", ["job_type"])
    op.create_index(
        "ix_jobs_project_status",
        "jobs",
        ["project_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_project_status", table_name="jobs")
    op.drop_index("ix_jobs_job_type", table_name="jobs")
    op.drop_index("ix_jobs_parent_job_id", table_name="jobs")
    op.drop_index("ix_jobs_project_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_celery_task_id", table_name="jobs")
    op.drop_table("jobs")
