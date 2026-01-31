"""Update segment and subscription enum types

The coordinate→segment rename changed enum values:
- SegmentType: COORDINATE → SEGMENT
- EventType: COORDINATE_COMPLETED → SEGMENT_COMPLETED, COORDINATE_FAILED → SEGMENT_FAILED

This migration updates the column types and migrates any old enum values.

Revision ID: d8d116c6e6a5
Revises: a1b2c3d4e5f6
Create Date: 2026-01-31 11:02:08.371337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8d116c6e6a5'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New enum definitions
segment_type_enum = sa.Enum('SHOW', 'MOVEMENT', 'SET', 'SEGMENT', name='segmenttype')
event_type_enum = sa.Enum(
    'REP_COMPLETED', 'REP_FAILED', 'REP_ASSIGNED',
    'SEGMENT_COMPLETED', 'SEGMENT_FAILED',
    'PROBLEM_POSTED', 'PROBLEM_RESOLVED',
    name='eventtype',
)


def upgrade() -> None:
    """Upgrade: rename old enum values, then alter column types."""
    # Migrate data: rename old enum values before changing column type
    op.execute("UPDATE segments SET type = 'SEGMENT' WHERE type = 'COORDINATE'")
    op.execute("UPDATE subscriptions SET event_type = 'SEGMENT_COMPLETED' WHERE event_type = 'COORDINATE_COMPLETED'")
    op.execute("UPDATE subscriptions SET event_type = 'SEGMENT_FAILED' WHERE event_type = 'COORDINATE_FAILED'")

    # Corps status renames: REHEARSAL → WINTER_CAMPS, TOUR → ON_TOUR
    # SQLAlchemy Enum stores .name (uppercase) for PEP-435 enums.
    op.execute("UPDATE corps SET status = 'WINTER_CAMPS' WHERE status = 'REHEARSAL'")
    op.execute("UPDATE corps SET status = 'ON_TOUR' WHERE status = 'TOUR'")

    with op.batch_alter_table('segments', schema=None) as batch_op:
        batch_op.alter_column('type',
               existing_type=sa.VARCHAR(length=10),
               type_=segment_type_enum,
               existing_nullable=False)

    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.alter_column('event_type',
               existing_type=sa.VARCHAR(length=20),
               type_=event_type_enum,
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade: revert column types, then rename SEGMENT→COORDINATE in data."""
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.alter_column('event_type',
               existing_type=event_type_enum,
               type_=sa.VARCHAR(length=20),
               existing_nullable=False)

    with op.batch_alter_table('segments', schema=None) as batch_op:
        batch_op.alter_column('type',
               existing_type=segment_type_enum,
               type_=sa.VARCHAR(length=10),
               existing_nullable=False)

    # Migrate data back to old enum values
    op.execute("UPDATE segments SET type = 'COORDINATE' WHERE type = 'SEGMENT'")
    op.execute("UPDATE subscriptions SET event_type = 'COORDINATE_COMPLETED' WHERE event_type = 'SEGMENT_COMPLETED'")
    op.execute("UPDATE subscriptions SET event_type = 'COORDINATE_FAILED' WHERE event_type = 'SEGMENT_FAILED'")

    # Revert corps status renames
    op.execute("UPDATE corps SET status = 'REHEARSAL' WHERE status = 'WINTER_CAMPS'")
    op.execute("UPDATE corps SET status = 'TOUR' WHERE status = 'ON_TOUR'")
