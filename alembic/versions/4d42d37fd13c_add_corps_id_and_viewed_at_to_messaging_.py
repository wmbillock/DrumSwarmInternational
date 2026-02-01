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
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
