"""ticket due_date

Revision ID: 004
Revises: 003
Create Date: 2025-01-01 00:00:04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("due_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "due_date")
