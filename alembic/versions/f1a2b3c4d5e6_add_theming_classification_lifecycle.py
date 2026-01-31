"""Add corps theming, agent classification, performer age, experience & self-improvement tables

Revision ID: f1a2b3c4d5e6
Revises: d8d116c6e6a5
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'd8d116c6e6a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table, col):
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == col for row in result)


def _has_table(conn, table):
    result = conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
    ), {"name": table})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # --- Phase 1: Corps theming ---
    if not _has_column(conn, 'corps', 'theme_id'):
        with op.batch_alter_table('corps') as batch_op:
            batch_op.add_column(sa.Column('theme_id', sa.String(50), nullable=True))
            batch_op.add_column(sa.Column('mascot', sa.String(100), nullable=True))
            batch_op.add_column(sa.Column('uniform_concept', sa.Text(), nullable=True))

    # --- Phase 2: Agent classification ---
    if not _has_column(conn, 'agent_definitions', 'classification'):
        with op.batch_alter_table('agent_definitions') as batch_op:
            batch_op.add_column(sa.Column('classification', sa.String(30), nullable=True))

        # Backfill classifications
        admin_roles = ('executive_director', 'program_coordinator', 'drum_major')
        for role in admin_roles:
            conn.execute(sa.text(
                f"UPDATE agent_definitions SET classification = 'administrative_staff' WHERE role = :role"
            ), {"role": role})

        instructional_roles = (
            'drill_writer', 'music_writer', 'choreographer',
            'brass_caption_head', 'percussion_caption_head',
            'guard_caption_head', 'visual_caption_head',
            'brass_tech', 'percussion_tech', 'front_ensemble_tech',
            'guard_tech', 'visual_tech',
        )
        for role in instructional_roles:
            conn.execute(sa.text(
                f"UPDATE agent_definitions SET classification = 'instructional_staff' WHERE role = :role"
            ), {"role": role})

        conn.execute(sa.text(
            "UPDATE agent_definitions SET classification = 'dci_assigned' WHERE role = 'timing_judge'"
        ))

    # --- Phase 4: Performer age fields ---
    if not _has_column(conn, 'performers', 'age'):
        with op.batch_alter_table('performers') as batch_op:
            batch_op.add_column(sa.Column('age', sa.Integer(), nullable=False, server_default='16'))
            batch_op.add_column(sa.Column('experience_seasons', sa.Integer(), nullable=False, server_default='0'))

    # --- Phase 4: Agent experience table ---
    if not _has_table(conn, 'agent_experience'):
        op.create_table(
            'agent_experience',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('performer_id', sa.String(36), sa.ForeignKey('performers.id'), nullable=False),
            sa.Column('activity_type', sa.String(50), nullable=False),
            sa.Column('show_id', sa.String(36), nullable=True),
            sa.Column('corps_id', sa.String(36), nullable=True),
            sa.Column('learned_skills', sa.Text(), nullable=True),
            sa.Column('achievements', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # --- Phase 4: Self-improvement log table ---
    if not _has_table(conn, 'self_improvement_log'):
        op.create_table(
            'self_improvement_log',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('agent_definition_id', sa.String(36), sa.ForeignKey('agent_definitions.id'), nullable=False),
            sa.Column('old_version', sa.Integer(), nullable=False),
            sa.Column('new_version', sa.Integer(), nullable=False),
            sa.Column('changes', sa.Text(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('approved_by', sa.String(36), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # --- Phase 5: Agent memory table ---
    if not _has_table(conn, 'agent_memory'):
        op.create_table(
            'agent_memory',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('agent_identity', sa.String(100), nullable=False, index=True),
            sa.Column('memory_type', sa.String(30), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
            sa.Column('source_session_id', sa.String(36), nullable=True),
            sa.Column('source_task', sa.Text(), nullable=True),
            sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('superseded_by', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # --- Phase 5: Task memory table ---
    if not _has_table(conn, 'task_memory'):
        op.create_table(
            'task_memory',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('session_id', sa.String(36), nullable=False, index=True),
            sa.Column('agent_identity', sa.String(100), nullable=False, index=True),
            sa.Column('task_hash', sa.String(64), nullable=False, index=True),
            sa.Column('tool_calls', sa.Text(), nullable=True),
            sa.Column('outcomes', sa.Text(), nullable=True),
            sa.Column('checkpoints', sa.Text(), nullable=True),
            sa.Column('result_summary', sa.Text(), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table('task_memory')
    op.drop_table('agent_memory')
    op.drop_table('self_improvement_log')
    op.drop_table('agent_experience')

    with op.batch_alter_table('performers') as batch_op:
        batch_op.drop_column('experience_seasons')
        batch_op.drop_column('age')

    with op.batch_alter_table('agent_definitions') as batch_op:
        batch_op.drop_column('classification')

    with op.batch_alter_table('corps') as batch_op:
        batch_op.drop_column('uniform_concept')
        batch_op.drop_column('mascot')
        batch_op.drop_column('theme_id')
