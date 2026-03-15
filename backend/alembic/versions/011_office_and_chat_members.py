"""office flag and chat members

Revision ID: 011
Revises: 010
Create Date: 2025-01-01 00:00:11

"""
from typing import Sequence, Union

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_office BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_members (
            chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (chat_id, user_id)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_members")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_office")
