"""Add model_specs and corps_strategies tables.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa

revision = "b3c4d5e6f7a8"
down_revision = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_specs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_id", sa.String(200), nullable=False),
        sa.Column("lora_id", sa.String(200), nullable=True),
        sa.Column("adapter_path", sa.Text, nullable=True),
        sa.Column("task_categories", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "corps_strategies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("corps_id", sa.String(36), sa.ForeignKey("corps.id"), nullable=False),
        sa.Column("model_policy", sa.String(30), nullable=False),
        sa.Column("preferred_provider", sa.String(50), nullable=True),
        sa.Column("risk_tolerance", sa.Float, server_default="0.5"),
        sa.Column("exploration_rate", sa.Float, server_default="0.1"),
        sa.Column("adaptation_style", sa.String(20), server_default="'prompt_only'"),
        sa.Column("section_overrides", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("corps_id", name="uq_corps_strategy_corps_id"),
    )


def downgrade() -> None:
    op.drop_table("corps_strategies")
    op.drop_table("model_specs")
