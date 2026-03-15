"""user profile position department

Revision ID: 009
Revises: 008
Create Date: 2025-01-01 00:00:09

"""
from typing import Sequence, Union

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS position VARCHAR(255) NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(255) NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS position")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS department")
