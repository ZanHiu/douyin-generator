"""add editor draft fields

Revision ID: 0006_edit_drafts
Revises: 0005_job_task_cancel
Create Date: 2026-06-17 21:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_edit_drafts"
down_revision = "0005_job_task_cancel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_edits", sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("job_edits", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.alter_column("job_edits", "output_video_path", existing_type=sa.Text(), nullable=True)
    op.alter_column("job_edits", "result_url", existing_type=sa.Text(), nullable=True)
    op.alter_column("job_edits", "is_draft", server_default=None)


def downgrade() -> None:
    op.alter_column("job_edits", "result_url", existing_type=sa.Text(), nullable=False)
    op.alter_column("job_edits", "output_video_path", existing_type=sa.Text(), nullable=False)
    op.drop_column("job_edits", "updated_at")
    op.drop_column("job_edits", "is_draft")
