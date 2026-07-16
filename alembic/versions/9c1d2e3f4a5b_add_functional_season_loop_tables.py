"""add functional season loop tables

Revision ID: 9c1d2e3f4a5b
Revises: f49a72b1c3d5
Create Date: 2026-07-14 05:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c1d2e3f4a5b"
down_revision: Union[str, None] = "f49a72b1c3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    if not _column_exists("performers", "corps_id"):
        op.add_column("performers", sa.Column("corps_id", sa.String(36), nullable=True))
        op.create_index("ix_performers_corps_id", "performers", ["corps_id"])

    if not _column_exists("scores", "season_event_id"):
        op.add_column("scores", sa.Column("season_event_id", sa.String(36), nullable=True))
        op.create_index("ix_scores_season_event_id", "scores", ["season_event_id"])

    if not _column_exists("scores", "artifact_id"):
        op.add_column("scores", sa.Column("artifact_id", sa.String(100), nullable=True))
        op.create_index("ix_scores_artifact_id", "scores", ["artifact_id"])

    if not _table_exists("season_runs"):
        op.create_table(
            "season_runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("regular_show_count", sa.Integer, nullable=False),
            sa.Column("winter_camp_count", sa.Integer, nullable=False),
            sa.Column("current_event_index", sa.Integer, nullable=False),
            sa.Column("blocker_reason", sa.Text, nullable=True),
        )

    if not _table_exists("season_events"):
        op.create_table(
            "season_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("season_run_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("sequence_index", sa.Integer, nullable=False),
            sa.Column("blocker_reason", sa.Text, nullable=True),
        )
        op.create_index("ix_season_events_season_run_id", "season_events", ["season_run_id"])

    if not _table_exists("corps_season_states"):
        op.create_table(
            "corps_season_states",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("season_run_id", sa.String(36), nullable=False),
            sa.Column("corps_id", sa.String(36), nullable=False),
            sa.Column("phase", sa.String(50), nullable=False),
            sa.Column("prestige_snapshot", sa.Float, nullable=False),
            sa.Column("cachet_snapshot", sa.Float, nullable=False),
            sa.Column("blocker_reason", sa.Text, nullable=True),
        )
        op.create_index("ix_corps_season_states_season_run_id", "corps_season_states", ["season_run_id"])
        op.create_index("ix_corps_season_states_corps_id", "corps_season_states", ["corps_id"])

    if not _table_exists("corps_event_states"):
        op.create_table(
            "corps_event_states",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("season_event_id", sa.String(36), nullable=False),
            sa.Column("corps_id", sa.String(36), nullable=False),
            sa.Column("phase", sa.String(50), nullable=False),
            sa.Column("blocker_reason", sa.Text, nullable=True),
        )
        op.create_index("ix_corps_event_states_season_event_id", "corps_event_states", ["season_event_id"])
        op.create_index("ix_corps_event_states_corps_id", "corps_event_states", ["corps_id"])

    if not _table_exists("rehearsal_blocks"):
        op.create_table(
            "rehearsal_blocks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("season_run_id", sa.String(36), nullable=False),
            sa.Column("season_event_id", sa.String(36), nullable=True),
            sa.Column("corps_id", sa.String(36), nullable=False),
            sa.Column("block_type", sa.String(50), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("sequence_index", sa.Integer, nullable=False),
            sa.Column("summary", sa.Text, nullable=True),
        )
        op.create_index("ix_rehearsal_blocks_season_run_id", "rehearsal_blocks", ["season_run_id"])
        op.create_index("ix_rehearsal_blocks_season_event_id", "rehearsal_blocks", ["season_event_id"])
        op.create_index("ix_rehearsal_blocks_corps_id", "rehearsal_blocks", ["corps_id"])

    if not _table_exists("mission_packets"):
        op.create_table(
            "mission_packets",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("session_id", sa.String(36), nullable=False),
            sa.Column("corps_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("phase", sa.String(50), nullable=False),
            sa.Column("target_type", sa.String(50), nullable=False),
            sa.Column("target_id", sa.String(100), nullable=False),
            sa.Column("allowed_tools", sa.JSON, nullable=True),
            sa.Column("forbidden_scope", sa.JSON, nullable=True),
            sa.Column("completion_criteria", sa.Text, nullable=False),
            sa.Column("handoff_target", sa.String(50), nullable=True),
        )
        op.create_index("ix_mission_packets_session_id", "mission_packets", ["session_id"], unique=True)
        op.create_index("ix_mission_packets_corps_id", "mission_packets", ["corps_id"])
        op.create_index("ix_mission_packets_target_id", "mission_packets", ["target_id"])

    if not _table_exists("judging_tapes"):
        op.create_table(
            "judging_tapes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("season_event_id", sa.String(36), nullable=False),
            sa.Column("corps_id", sa.String(36), nullable=False),
            sa.Column("rep_id", sa.String(36), nullable=True),
            sa.Column("artifact_id", sa.String(100), nullable=True),
            sa.Column("caption", sa.String(50), nullable=False),
            sa.Column("tape_text", sa.Text, nullable=False),
        )
        op.create_index("ix_judging_tapes_season_event_id", "judging_tapes", ["season_event_id"])
        op.create_index("ix_judging_tapes_corps_id", "judging_tapes", ["corps_id"])
        op.create_index("ix_judging_tapes_rep_id", "judging_tapes", ["rep_id"])
        op.create_index("ix_judging_tapes_artifact_id", "judging_tapes", ["artifact_id"])

    if not _table_exists("critique_adjustments"):
        op.create_table(
            "critique_adjustments",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("season_event_id", sa.String(36), nullable=False),
            sa.Column("corps_id", sa.String(36), nullable=False),
            sa.Column("corps_event_state_id", sa.String(36), nullable=False),
            sa.Column("caption", sa.String(50), nullable=False),
            sa.Column("source_tape_id", sa.String(36), nullable=False),
            sa.Column("action_summary", sa.Text, nullable=False),
        )
        op.create_index("ix_critique_adjustments_season_event_id", "critique_adjustments", ["season_event_id"])
        op.create_index("ix_critique_adjustments_corps_id", "critique_adjustments", ["corps_id"])
        op.create_index("ix_critique_adjustments_corps_event_state_id", "critique_adjustments", ["corps_event_state_id"])
        op.create_index("ix_critique_adjustments_source_tape_id", "critique_adjustments", ["source_tape_id"])


def downgrade() -> None:
    for table in (
        "critique_adjustments",
        "judging_tapes",
        "mission_packets",
        "rehearsal_blocks",
        "corps_event_states",
        "corps_season_states",
        "season_events",
        "season_runs",
    ):
        if _table_exists(table):
            op.drop_table(table)

    if _column_exists("scores", "artifact_id"):
        op.drop_index("ix_scores_artifact_id", table_name="scores")
        op.drop_column("scores", "artifact_id")
    if _column_exists("scores", "season_event_id"):
        op.drop_index("ix_scores_season_event_id", table_name="scores")
        op.drop_column("scores", "season_event_id")
    if _column_exists("performers", "corps_id"):
        op.drop_index("ix_performers_corps_id", table_name="performers")
        op.drop_column("performers", "corps_id")
