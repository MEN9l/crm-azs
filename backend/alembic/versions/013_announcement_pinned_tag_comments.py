"""announcement: is_pinned, is_important, tag; announcement_comments

Revision ID: 013
Revises: 012
Create Date: 2025-01-01 00:00:13

"""
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS is_important BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE announcements ADD COLUMN IF NOT EXISTS tag VARCHAR(100) NULL")
    op.execute("""
        CREATE TABLE IF NOT EXISTS announcement_comments (
            id SERIAL PRIMARY KEY,
            announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
            author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_announcement_comments_announcement_id ON announcement_comments(announcement_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_announcement_comments_author_id ON announcement_comments(author_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS announcement_comments")
    op.execute("ALTER TABLE announcements DROP COLUMN IF EXISTS tag")
    op.execute("ALTER TABLE announcements DROP COLUMN IF EXISTS is_important")
    op.execute("ALTER TABLE announcements DROP COLUMN IF EXISTS is_pinned")
