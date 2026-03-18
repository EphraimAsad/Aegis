"""Create job_progress_logs table.

Revision ID: 004
Revises: 003
Create Date: 2026-03-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create job_progress_logs table
    op.create_table(
        "job_progress_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # Link to job
        sa.Column("job_id", sa.Integer(), nullable=False),
        # Entry type and phase
        sa.Column("entry_type", sa.String(length=50), nullable=False),
        sa.Column("phase", sa.String(length=100), nullable=True),
        # Message and data
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Checkpoint fields
        sa.Column("is_checkpoint", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("checkpoint_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Ordering
        sa.Column("sequence", sa.Integer(), nullable=False),
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
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_job_progress_logs_job_id",
        "job_progress_logs",
        ["job_id"],
    )
    op.create_index(
        "ix_job_progress_logs_entry_type",
        "job_progress_logs",
        ["entry_type"],
    )
    op.create_index(
        "ix_job_progress_logs_phase",
        "job_progress_logs",
        ["phase"],
    )
    op.create_index(
        "ix_job_progress_logs_is_checkpoint",
        "job_progress_logs",
        ["is_checkpoint"],
    )
    op.create_index(
        "ix_job_progress_logs_sequence",
        "job_progress_logs",
        ["sequence"],
    )
    # Composite index for common query: get job's checkpoints ordered
    op.create_index(
        "ix_job_progress_logs_job_checkpoint",
        "job_progress_logs",
        ["job_id", "is_checkpoint", "sequence"],
    )
    # Composite index for getting job entries by type
    op.create_index(
        "ix_job_progress_logs_job_type",
        "job_progress_logs",
        ["job_id", "entry_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_progress_logs_job_type", table_name="job_progress_logs")
    op.drop_index("ix_job_progress_logs_job_checkpoint", table_name="job_progress_logs")
    op.drop_index("ix_job_progress_logs_sequence", table_name="job_progress_logs")
    op.drop_index("ix_job_progress_logs_is_checkpoint", table_name="job_progress_logs")
    op.drop_index("ix_job_progress_logs_phase", table_name="job_progress_logs")
    op.drop_index("ix_job_progress_logs_entry_type", table_name="job_progress_logs")
    op.drop_index("ix_job_progress_logs_job_id", table_name="job_progress_logs")
    op.drop_table("job_progress_logs")
