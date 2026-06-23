"""add job final config

Revision ID: 0004_add_job_final_config
Revises: 0003_add_job_edits
Create Date: 2026-06-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_add_job_final_config"
down_revision: str | None = "0003_add_job_edits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("final_config_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "final_config_json")
