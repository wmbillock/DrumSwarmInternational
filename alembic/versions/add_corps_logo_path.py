"""Add logo_path column to corps table.

Revision ID: b3c4d5e6f7g8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7g8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("corps", sa.Column("logo_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("corps", "logo_path")
