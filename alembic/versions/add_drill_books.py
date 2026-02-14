"""Add drill books, drill steps, drill evidence tables.

Revision ID: a2b3c4d5e6f7
Revises: 1bb647bf67c0
Create Date: 2026-02-09
"""

from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f7"
down_revision = "1bb647bf67c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drill_books",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("drill_books.id"), nullable=True),
        sa.Column("corps_id", sa.String(36), sa.ForeignKey("corps.id"), nullable=True),
        sa.Column("assigned_performer_id", sa.String(36), sa.ForeignKey("performers.id"), nullable=True),
        sa.Column("assigned_role", sa.String(50), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("book_type", sa.String(20), server_default="linear"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context_summary", sa.Text, nullable=True),
        sa.Column("context_snapshot", sa.JSON, nullable=True),
    )

    op.create_table(
        "drill_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("book_id", sa.String(36), sa.ForeignKey("drill_books.id"), nullable=False),
        sa.Column("sequence", sa.Integer, server_default="0"),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("depends_on", sa.JSON, nullable=True),
        sa.Column("next_steps", sa.JSON, nullable=True),
        sa.Column("assigned_session_id", sa.String(36), sa.ForeignKey("agent_sessions.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )

    op.create_table(
        "drill_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("book_id", sa.String(36), sa.ForeignKey("drill_books.id"), nullable=False),
        sa.Column("step_id", sa.String(36), sa.ForeignKey("drill_steps.id"), nullable=True),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("drill_evidence")
    op.drop_table("drill_steps")
    op.drop_table("drill_books")
