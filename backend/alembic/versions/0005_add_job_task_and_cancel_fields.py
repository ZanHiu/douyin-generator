"""add job task and cancel fields

Revision ID: 0005_job_task_cancel
Revises: 0004_add_job_final_config
Create Date: 2026-06-17 14:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_job_task_cancel"
down_revision = "0004_add_job_final_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("jobs", sa.Column("task_id", sa.String(length=64), nullable=True))
    op.alter_column("jobs", "cancel_requested", server_default=None)


def downgrade() -> None:
    op.drop_column("jobs", "task_id")
    op.drop_column("jobs", "cancel_requested")
