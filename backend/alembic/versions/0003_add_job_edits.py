"""add job edits

Revision ID: 0003_add_job_edits
Revises: 0002_add_job_storage_dir
Create Date: 2026-06-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_job_edits"
down_revision: str | None = "0002_add_job_storage_dir"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_edits",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("tool_summary", sa.String(length=128), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("output_video_path", sa.Text(), nullable=False),
        sa.Column("result_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_job_edits_job_id", "job_edits", ["job_id"])
    op.create_index("ix_job_edits_created_at", "job_edits", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_job_edits_created_at", table_name="job_edits")
    op.drop_index("ix_job_edits_job_id", table_name="job_edits")
    op.drop_table("job_edits")
