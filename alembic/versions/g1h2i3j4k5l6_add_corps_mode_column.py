"""Add mode column to corps table.

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa

revision = "g1h2i3j4k5l6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "corps",
        sa.Column(
            "mode",
            sa.Enum(
                "design_room", "show_mode", "rehearsal_mode", "judging", "offseason_review",
                name="corpsmode",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("corps", "mode")
