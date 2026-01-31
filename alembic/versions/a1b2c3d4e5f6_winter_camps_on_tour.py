"""Rename rehearsal/tour to winter_camps/on_tour, drop tour_mode

Revision ID: a1b2c3d4e5f6
Revises: 365ea178faf0
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '365ea178faf0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table, col):
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == col for row in result)


def upgrade() -> None:
    """Rename status enum values and drop tour_mode column."""
    conn = op.get_bind()

    # 1. Rename status values: rehearsal → winter_camps, tour → on_tour
    conn.execute(sa.text(
        "UPDATE corps SET status = 'winter_camps' WHERE status = 'rehearsal'"
    ))
    conn.execute(sa.text(
        "UPDATE corps SET status = 'on_tour' WHERE status = 'tour'"
    ))

    # 2. Drop tour_mode column (SQLite requires table rebuild)
    if _has_column(conn, 'corps', 'tour_mode'):
        # SQLite doesn't support DROP COLUMN before 3.35.0, use batch mode
        with op.batch_alter_table('corps') as batch_op:
            batch_op.drop_column('tour_mode')

    # 3. Set rehearsal_mode=basics for any winter_camps corps without a mode
    conn.execute(sa.text(
        "UPDATE corps SET rehearsal_mode = 'basics' "
        "WHERE status = 'winter_camps' AND rehearsal_mode IS NULL"
    ))


def downgrade() -> None:
    """Restore old status values and add back tour_mode."""
    conn = op.get_bind()

    # Re-add tour_mode column
    with op.batch_alter_table('corps') as batch_op:
        batch_op.add_column(sa.Column('tour_mode', sa.Boolean(), nullable=False, server_default='0'))

    # Rename status values back
    conn.execute(sa.text(
        "UPDATE corps SET status = 'rehearsal' WHERE status = 'winter_camps'"
    ))
    conn.execute(sa.text(
        "UPDATE corps SET status = 'tour' WHERE status = 'on_tour'"
    ))

    # Set tour_mode for on_tour corps
    conn.execute(sa.text(
        "UPDATE corps SET tour_mode = 1 WHERE status = 'tour'"
    ))
