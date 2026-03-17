"""tasks: department executor

Revision ID: 016
Revises: 015
Create Date: 2026-03-17 00:00:16

"""
from typing import Sequence, Union

from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS department_id INTEGER NULL REFERENCES departments(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tasks_department_id ON tasks(department_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE tasks DROP COLUMN IF EXISTS department_id")

