"""departments hierarchy + routing fields

Revision ID: 014
Revises: 013
Create Date: 2026-03-17 00:00:14

"""
from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            parent_id INTEGER NULL REFERENCES departments(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL DEFAULT (CURRENT_TIMESTAMP)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_departments_name ON departments(name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_departments_parent_id ON departments(parent_id)")

    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(255) NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS department_id INTEGER NULL REFERENCES departments(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_department_id ON users(department_id)")

    op.execute("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS department_id INTEGER NULL REFERENCES departments(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tickets_department_id ON tickets(department_id)")

    # Backfill: create root departments from existing users.department strings
    op.execute(
        """
        INSERT INTO departments(name)
        SELECT DISTINCT TRIM(department) AS name
        FROM users
        WHERE department IS NOT NULL AND TRIM(department) <> ''
        ON CONFLICT (name) DO NOTHING
        """
    )
    # Backfill: assign users.department_id based on name match
    op.execute(
        """
        UPDATE users u
        SET department_id = d.id
        FROM departments d
        WHERE u.department_id IS NULL
          AND u.department IS NOT NULL
          AND TRIM(u.department) <> ''
          AND d.name = TRIM(u.department)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tickets DROP COLUMN IF EXISTS department_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS department_id")
    # department text column existed earlier in code; keep it to avoid data loss
    op.execute("DROP TABLE IF EXISTS departments")

