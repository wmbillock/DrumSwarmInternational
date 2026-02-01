"""add_corps_id_and_viewed_at_to_messaging_threads

Revision ID: 4d42d37fd13c
Revises: 4fc336742c84
Create Date: 2026-02-01 02:15:30.962516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d42d37fd13c'
down_revision: Union[str, Sequence[str], None] = '4fc336742c84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to messaging_threads
    op.add_column('messaging_threads', sa.Column('corps_id', sa.String(36), nullable=True))
    op.add_column('messaging_threads', sa.Column('initiator_agent_id', sa.String(36), nullable=True))
    op.add_column('messaging_threads', sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True))

    # Add foreign key constraints (SQLite requires special handling for FK constraints)
    # For SQLite, we need to recreate the table to add FK constraints
    # For now, we'll just add the columns without FK constraints
    # The application will enforce referential integrity


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messaging_threads', 'viewed_at')
    op.drop_column('messaging_threads', 'initiator_agent_id')
    op.drop_column('messaging_threads', 'corps_id')
