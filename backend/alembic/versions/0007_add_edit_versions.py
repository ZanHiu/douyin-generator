"""add version number for job edits

Revision ID: 0007_add_edit_versions
Revises: 0006_edit_drafts
Create Date: 2026-06-20 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_add_edit_versions"
down_revision = "0006_edit_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_edits", sa.Column("version_number", sa.Integer(), nullable=True))

    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY job_id
                    ORDER BY created_at ASC, id ASC
                ) AS version_number
            FROM job_edits
            WHERE is_draft = FALSE
        )
        UPDATE job_edits
        SET version_number = ranked.version_number
        FROM ranked
        WHERE job_edits.id = ranked.id
        """
    )


def downgrade() -> None:
    op.drop_column("job_edits", "version_number")
