"""Add model_spec_performances table.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_spec_performances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("model_spec_id", sa.String(36), sa.ForeignKey("model_specs.id"), nullable=False),
        sa.Column("task_category", sa.String(50), nullable=False),
        sa.Column("corps_id", sa.String(36), sa.ForeignKey("corps.id"), nullable=True),
        sa.Column("total_attempts", sa.Integer, server_default="0"),
        sa.Column("successful_attempts", sa.Integer, server_default="0"),
        sa.Column("total_score", sa.Float, server_default="0.0"),
        sa.Column("avg_score", sa.Float, server_default="0.0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("model_spec_id", "task_category", "corps_id", name="uq_msp_spec_category_corps"),
    )


def downgrade() -> None:
    op.drop_table("model_spec_performances")
