"""remove general chat

Revision ID: 018
Revises: 017
Create Date: 2026-03-17 01:10:00

"""
from typing import Sequence, Union

from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # удаляем общий чат и его сообщения (если он есть)
    op.execute("DELETE FROM messages WHERE chat_id IN (SELECT id FROM chats WHERE type = 'general')")
    op.execute("DELETE FROM chat_members WHERE chat_id IN (SELECT id FROM chats WHERE type = 'general')")
    op.execute("DELETE FROM chats WHERE type = 'general'")


def downgrade() -> None:
    # не восстанавливаем удалённые данные
    pass

