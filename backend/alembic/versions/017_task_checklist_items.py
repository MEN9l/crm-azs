"""task checklist items

Revision ID: 017
Revises: 016
Create Date: 2026-03-17 00:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_checklist_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("station_name", sa.String(255), nullable=False),
        sa.Column("is_done", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("done_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("done_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"])
    op.create_index("ix_task_checklist_items_is_done", "task_checklist_items", ["is_done"])


def downgrade() -> None:
    op.drop_index("ix_task_checklist_items_is_done", table_name="task_checklist_items")
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")

