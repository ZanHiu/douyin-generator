"""add job queue metadata

Revision ID: 0010_job_queue_metadata
Revises: 0009_user_settings_json
Create Date: 2026-06-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010_job_queue_metadata"
down_revision: str | Sequence[str] | None = "0009_user_settings_json"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("jobs", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE jobs SET queued_at = created_at WHERE queued_at IS NULL")
    op.alter_column("jobs", "retry_count", server_default=None)


def downgrade() -> None:
    op.drop_column("jobs", "cancel_requested_at")
    op.drop_column("jobs", "started_at")
    op.drop_column("jobs", "queued_at")
    op.drop_column("jobs", "retry_count")
