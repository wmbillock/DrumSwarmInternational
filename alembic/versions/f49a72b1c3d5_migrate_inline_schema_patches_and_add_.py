"""migrate inline schema patches and add remaining tables

Revision ID: f49a72b1c3d5
Revises: e384c993d96f
Create Date: 2026-02-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f49a72b1c3d5'
down_revision: Union[str, None] = 'e384c993d96f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent migration)."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    return column in cols


def _table_exists(table: str) -> bool:
    """Check if a table already exists."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def upgrade() -> None:
    # --- Inline schema patches (previously in database.py _apply_schema_patches) ---

    if not _column_exists("agent_sessions", "performer_id"):
        op.add_column("agent_sessions", sa.Column("performer_id", sa.String(36), nullable=True))

    if not _column_exists("scores", "rep_score"):
        op.add_column("scores", sa.Column("rep_score", sa.Float, nullable=True))

    if not _column_exists("scores", "perf_score"):
        op.add_column("scores", sa.Column("perf_score", sa.Float, nullable=True))

    if not _column_exists("corps", "corps_type"):
        op.add_column("corps", sa.Column("corps_type", sa.String(20), server_default="competing", nullable=True))

    if not _column_exists("critique_sessions", "is_automated"):
        op.add_column("critique_sessions", sa.Column("is_automated", sa.Boolean, server_default="0", nullable=True))

    if not _column_exists("corps", "color_scheme"):
        op.add_column("corps", sa.Column("color_scheme", sa.Text, nullable=True))

    # --- New tables for metrics, agent memory, experiences, self-improvement ---

    if not _table_exists("metrics_events"):
        op.create_table(
            "metrics_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), index=True, nullable=False),
            sa.Column("metric_type", sa.String(50), index=True, nullable=False),
            sa.Column("corps_id", sa.String(36), index=True, nullable=True),
            sa.Column("agent_role", sa.String(50), nullable=True),
            sa.Column("rep_id", sa.String(36), nullable=True),
            sa.Column("segment_id", sa.String(36), nullable=True),
            sa.Column("session_id", sa.String(36), nullable=True),
            sa.Column("value", sa.Float, nullable=True),
            sa.Column("unit", sa.String(20), nullable=True),
            sa.Column("tags", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("metrics_aggregates"):
        op.create_table(
            "metrics_aggregates",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("bucket_start", sa.DateTime(timezone=True), index=True, nullable=False),
            sa.Column("window", sa.String(10), index=True, nullable=False),
            sa.Column("metric_type", sa.String(50), index=True, nullable=False),
            sa.Column("corps_id", sa.String(36), index=True, nullable=True),
            sa.Column("agent_role", sa.String(50), nullable=True),
            sa.Column("count", sa.Integer, default=0, nullable=False),
            sa.Column("sum_value", sa.Float, nullable=True),
            sa.Column("min_value", sa.Float, nullable=True),
            sa.Column("max_value", sa.Float, nullable=True),
            sa.Column("mean_value", sa.Float, nullable=True),
            sa.Column("p50_value", sa.Float, nullable=True),
            sa.Column("p95_value", sa.Float, nullable=True),
            sa.Column("p99_value", sa.Float, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("metrics_trends"):
        op.create_table(
            "metrics_trends",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("period_start", sa.DateTime(timezone=True), index=True, nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_days", sa.Integer, nullable=False),
            sa.Column("metric_type", sa.String(50), index=True, nullable=False),
            sa.Column("corps_id", sa.String(36), nullable=True),
            sa.Column("agent_role", sa.String(50), nullable=True),
            sa.Column("avg_value", sa.Float, nullable=True),
            sa.Column("prev_period_avg", sa.Float, nullable=True),
            sa.Column("rate_of_change", sa.Float, nullable=True),
            sa.Column("trend_direction", sa.String(10), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("agent_experience"):
        op.create_table(
            "agent_experience",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("corps_id", sa.String(36), index=True, nullable=False),
            sa.Column("role", sa.String(50), index=True, nullable=False),
            sa.Column("session_id", sa.String(36), nullable=True),
            sa.Column("task_category", sa.String(100), index=True, nullable=True),
            sa.Column("task_description", sa.Text, nullable=True),
            sa.Column("approach_used", sa.Text, nullable=True),
            sa.Column("outcome", sa.String(20), nullable=True),
            sa.Column("score", sa.Float, nullable=True),
            sa.Column("lessons_learned", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("agent_memory"):
        op.create_table(
            "agent_memory",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("corps_id", sa.String(36), index=True, nullable=False),
            sa.Column("role", sa.String(50), index=True, nullable=False),
            sa.Column("memory_type", sa.String(30), nullable=False),
            sa.Column("key", sa.String(200), index=True, nullable=False),
            sa.Column("value", sa.Text, nullable=False),
            sa.Column("confidence", sa.Float, nullable=True),
            sa.Column("source_session_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("task_memory"):
        op.create_table(
            "task_memory",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("corps_id", sa.String(36), index=True, nullable=False),
            sa.Column("task_category", sa.String(100), index=True, nullable=False),
            sa.Column("best_approach", sa.Text, nullable=True),
            sa.Column("common_pitfalls", sa.Text, nullable=True),
            sa.Column("success_count", sa.Integer, default=0),
            sa.Column("failure_count", sa.Integer, default=0),
            sa.Column("avg_score", sa.Float, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("self_improvement_log"):
        op.create_table(
            "self_improvement_log",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("corps_id", sa.String(36), index=True, nullable=False),
            sa.Column("role", sa.String(50), nullable=True),
            sa.Column("improvement_type", sa.String(50), nullable=False),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("before_state", sa.Text, nullable=True),
            sa.Column("after_state", sa.Text, nullable=True),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("result", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("corps_configs"):
        op.create_table(
            "corps_configs",
            sa.Column("corps_id", sa.String(36), primary_key=True),
            sa.Column("llm_provider", sa.String(50), nullable=True),
            sa.Column("llm_model_override", sa.String(100), nullable=True),
            sa.Column("methodology", sa.String(100), nullable=True),
            sa.Column("architecture_style", sa.String(100), nullable=True),
            sa.Column("coding_style", sa.String(100), nullable=True),
            sa.Column("extra", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("experiment_results"):
        op.create_table(
            "experiment_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("corps_id", sa.String(36), index=True, nullable=False),
            sa.Column("show_id", sa.String(36), nullable=True),
            sa.Column("competition_id", sa.String(100), nullable=True),
            sa.Column("season_id", sa.String(100), nullable=True),
            sa.Column("llm_provider", sa.String(50), nullable=True),
            sa.Column("llm_model", sa.String(100), nullable=True),
            sa.Column("methodology", sa.String(100), nullable=True),
            sa.Column("total_score", sa.Float, nullable=True),
            sa.Column("caption_scores", sa.Text, nullable=True),
            sa.Column("iterations_used", sa.Integer, nullable=True),
            sa.Column("tool_calls_count", sa.Integer, nullable=True),
            sa.Column("sessions_spawned", sa.Integer, nullable=True),
            sa.Column("failures_count", sa.Integer, nullable=True),
            sa.Column("wall_time_seconds", sa.Float, nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("metrics", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _table_exists("operations"):
        op.create_table(
            "operations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("operation_type", sa.String(50), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("target_type", sa.String(50), nullable=True),
            sa.Column("target_id", sa.String(36), nullable=True),
            sa.Column("label", sa.String(200), nullable=True),
            sa.Column("result", sa.Text, nullable=True),
            sa.Column("error", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    # Drop new tables (in reverse order of creation)
    for table in [
        "operations", "experiment_results", "corps_configs",
        "self_improvement_log", "task_memory", "agent_memory",
        "agent_experience", "metrics_trends", "metrics_aggregates",
        "metrics_events",
    ]:
        if _table_exists(table):
            op.drop_table(table)

    # Removing columns is not supported in SQLite ALTER TABLE
    # These columns are harmless if left in place
