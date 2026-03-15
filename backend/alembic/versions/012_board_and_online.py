"""board: announcements, polls, user last_seen_at

Revision ID: 012
Revises: 011
Create Date: 2025-01-01 00:00:12

"""
from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP NULL")
    op.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_announcements_author_id ON announcements(author_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            id SERIAL PRIMARY KEY,
            question VARCHAR(500) NOT NULL,
            created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP),
            closed_at TIMESTAMP NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_polls_created_by_id ON polls(created_by_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS poll_options (
            id SERIAL PRIMARY KEY,
            poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
            text VARCHAR(300) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_poll_options_poll_id ON poll_options(poll_id)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS poll_votes (
            id SERIAL PRIMARY KEY,
            poll_id INTEGER NOT NULL REFERENCES polls(id) ON DELETE CASCADE,
            option_id INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_poll_votes_poll_id ON poll_votes(poll_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_poll_votes_user_id ON poll_votes(user_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_poll_votes_user ON poll_votes(poll_id, user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS poll_votes")
    op.execute("DROP TABLE IF EXISTS poll_options")
    op.execute("DROP TABLE IF EXISTS polls")
    op.execute("DROP TABLE IF EXISTS announcements")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS last_seen_at")
