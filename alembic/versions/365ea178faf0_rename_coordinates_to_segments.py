"""rename coordinates to segments

Revision ID: 365ea178faf0
Revises: 0d46323a713e
Create Date: 2026-01-31 02:42:40.361718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '365ea178faf0'
down_revision: Union[str, Sequence[str], None] = '0d46323a713e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, name):
    result = conn.execute(sa.text(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=:n"
    ), {"n": name})
    return result.scalar() > 0


def _has_column(conn, table, col):
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    return any(row[1] == col for row in result)


def _rename_col(conn, table, old, new):
    if _has_column(conn, table, old):
        conn.execute(sa.text(f'ALTER TABLE {table} RENAME COLUMN {old} TO {new}'))


def upgrade() -> None:
    """Rename coordinates table to segments and update all FK columns."""
    conn = op.get_bind()

    # 1. Rename the main table if it still has the old name
    if _has_table(conn, 'coordinates') and not _has_table(conn, 'segments'):
        op.execute('ALTER TABLE coordinates RENAME TO segments')

    # 2. Rename FK columns (idempotent)
    _rename_col(conn, 'shows', 'coordinate_root_id', 'segment_root_id')
    _rename_col(conn, 'reps', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'scoresheets', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'messages', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'context_snapshots', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'work_logs', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'scores', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'penalties', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'problems', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'subscriptions', 'coordinate_id', 'segment_id')
    _rename_col(conn, 'capability_ledger', 'coordinate_id', 'segment_id')


def downgrade() -> None:
    """Revert segments back to coordinates."""
    op.execute('ALTER TABLE capability_ledger RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE scores RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE work_logs RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE context_snapshots RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE messages RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE scoresheets RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE reps RENAME COLUMN segment_id TO coordinate_id')
    op.execute('ALTER TABLE shows RENAME COLUMN segment_root_id TO coordinate_root_id')
    op.execute('ALTER TABLE segments RENAME TO coordinates')
