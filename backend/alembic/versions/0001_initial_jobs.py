"""initial jobs schema

Revision ID: 0001_initial_jobs
Revises:
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_jobs"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("voice_id", sa.String(length=128), nullable=True),
        sa.Column("burn_subtitle", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mix_original_audio", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("input_video_path", sa.Text(), nullable=True),
        sa.Column("audio_path", sa.Text(), nullable=True),
        sa.Column("transcript_zh_path", sa.Text(), nullable=True),
        sa.Column("transcript_vi_path", sa.Text(), nullable=True),
        sa.Column("subtitle_path", sa.Text(), nullable=True),
        sa.Column("tts_audio_path", sa.Text(), nullable=True),
        sa.Column("output_video_path", sa.Text(), nullable=True),
        sa.Column("result_url", sa.Text(), nullable=True),
        sa.Column("subtitle_url", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])

    op.create_table(
        "job_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_job_logs_job_id", "job_logs", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_logs_job_id", table_name="job_logs")
    op.drop_table("job_logs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
