"""add_messaging_system_tables

Revision ID: 57901e98cbc0
Revises: 5717763b1040
Create Date: 2026-02-01 02:14:20.321947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57901e98cbc0'
down_revision: Union[str, Sequence[str], None] = '5717763b1040'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create messaging_threads table
    op.create_table(
        'messaging_threads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('corps_id', sa.String(36), nullable=True),
        sa.Column('initiator_agent_id', sa.String(36), nullable=True),
        sa.Column('originator_role', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by', sa.String(36), nullable=True),
        sa.Column('archive_candidate_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['corps_id'], ['corps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['initiator_agent_id'], ['agent_sessions.id']),
    )

    # Create indexes for messaging_threads
    op.create_index('idx_threads_status_corps', 'messaging_threads', ['status', 'corps_id'])
    op.create_index('idx_threads_completed_at', 'messaging_threads', ['completed_at'])

    # Create thread_messages table
    op.create_table(
        'thread_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('thread_id', sa.String(36), nullable=False),
        sa.Column('sender_type', sa.String(20), nullable=False),
        sa.Column('sender_role', sa.String(50), nullable=False),
        sa.Column('sender_name', sa.String(255), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['thread_id'], ['messaging_threads.id'], ondelete='CASCADE'),
    )

    # Create index for thread_messages
    op.create_index('idx_messages_thread_time', 'thread_messages', ['thread_id', 'created_at'])

    # Create archived_threads table
    op.create_table(
        'archived_threads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('original_thread_id', sa.String(36), nullable=False),
        sa.Column('originator_role', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('message_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('archived_by', sa.String(36), nullable=False),
        sa.Column('full_text', sa.Text, nullable=False),
        sa.Column('tags', sa.String(500), nullable=True),
        sa.Column('decision', sa.Text, nullable=True),
    )

    # Create index for archived_threads
    op.create_index('idx_archived_threads_archived_at', 'archived_threads', ['archived_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_archived_threads_archived_at')
    op.drop_table('archived_threads')

    op.drop_index('idx_messages_thread_time')
    op.drop_table('thread_messages')

    op.drop_index('idx_threads_completed_at')
    op.drop_index('idx_threads_status_corps')
    op.drop_table('messaging_threads')
