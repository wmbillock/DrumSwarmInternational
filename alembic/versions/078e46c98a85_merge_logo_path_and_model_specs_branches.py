"""merge logo_path and model_specs branches

Revision ID: 078e46c98a85
Revises: b3c4d5e6f7g8, c4d5e6f7a8b9
Create Date: 2026-02-14 00:27:34.327628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '078e46c98a85'
down_revision: Union[str, Sequence[str], None] = ('b3c4d5e6f7g8', 'c4d5e6f7a8b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
