"""add artifacts and performance_records tables

Revision ID: e384c993d96f
Revises: 078e46c98a85
Create Date: 2026-02-14 10:52:09.436693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e384c993d96f'
down_revision: Union[str, Sequence[str], None] = '078e46c98a85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('artifacts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('artifact_type', sa.Enum('logo', 'spec', 'design_notes', 'show_prompt', 'post_mortem', 'standings', 'scores', 'critique', 'code', 'document', 'image', 'other', name='artifacttype'), nullable=False),
    sa.Column('file_path', sa.String(length=500), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=True),
    sa.Column('corps_id', sa.String(length=36), nullable=True),
    sa.Column('corps_name', sa.String(length=255), nullable=True),
    sa.Column('operation_id', sa.String(length=36), nullable=True),
    sa.Column('season_id', sa.String(length=100), nullable=True),
    sa.Column('show_slug', sa.String(length=255), nullable=True),
    sa.Column('competition_id', sa.String(length=200), nullable=True),
    sa.Column('size_bytes', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('performance_records',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('corps_id', sa.String(length=36), nullable=False),
    sa.Column('corps_name', sa.String(length=255), nullable=False),
    sa.Column('season_id', sa.String(length=100), nullable=False),
    sa.Column('competition_id', sa.String(length=200), nullable=False),
    sa.Column('show_slug', sa.String(length=255), nullable=False),
    sa.Column('round_number', sa.Integer(), nullable=False),
    sa.Column('placement', sa.Integer(), nullable=False),
    sa.Column('field_size', sa.Integer(), nullable=False),
    sa.Column('final_score', sa.Float(), nullable=False),
    sa.Column('raw_score', sa.Float(), nullable=False),
    sa.Column('caption_scores_json', sa.Text(), nullable=True),
    sa.Column('competed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('performance_records', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_performance_records_competition_id'), ['competition_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_performance_records_corps_id'), ['corps_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_performance_records_season_id'), ['season_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('performance_records', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_performance_records_season_id'))
        batch_op.drop_index(batch_op.f('ix_performance_records_corps_id'))
        batch_op.drop_index(batch_op.f('ix_performance_records_competition_id'))

    op.drop_table('performance_records')
    op.drop_table('artifacts')
