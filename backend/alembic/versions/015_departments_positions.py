"""departments: positions for org chart

Revision ID: 015
Revises: 014
Create Date: 2026-03-17 00:00:15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE departments ADD COLUMN IF NOT EXISTS pos_x INTEGER NULL")
    op.execute("ALTER TABLE departments ADD COLUMN IF NOT EXISTS pos_y INTEGER NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE departments DROP COLUMN IF EXISTS pos_x")
    op.execute("ALTER TABLE departments DROP COLUMN IF EXISTS pos_y")

