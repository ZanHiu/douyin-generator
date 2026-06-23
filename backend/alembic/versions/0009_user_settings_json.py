"""add user settings json

Revision ID: 0009_user_settings_json
Revises: 0008_auth_tables
Create Date: 2026-06-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009_user_settings_json"
down_revision: str | Sequence[str] | None = "0008_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("settings_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "settings_json")
