"""add sessions

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-20

"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE sessions (
            session_id  UUID PRIMARY KEY,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            status      TEXT NOT NULL DEFAULT 'active'
        )
    """)

    op.execute("""
        CREATE TABLE session_users (
            session_id  UUID NOT NULL REFERENCES sessions(session_id),
            user_id     BIGINT NOT NULL REFERENCES users(user_id),
            joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (session_id, user_id)
        )
    """)

    op.execute("""
        ALTER TABLE messages
        ADD COLUMN session_id UUID REFERENCES sessions(session_id)
    """)

    op.execute("CREATE INDEX ix_messages_session_id ON messages (session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_messages_session_id")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS session_id")
    op.execute("DROP TABLE IF EXISTS session_users")
    op.execute("DROP TABLE IF EXISTS sessions")
