"""add session_messages

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-20

"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE session_messages (
            session_id  UUID NOT NULL REFERENCES sessions(session_id),
            message_id  BIGINT NOT NULL REFERENCES messages(message_id),
            user_id     BIGINT NOT NULL REFERENCES users(user_id),
            added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (session_id, message_id)
        )
    """)
    op.execute("CREATE INDEX ix_session_messages_session_id ON session_messages (session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_session_messages_session_id")
    op.execute("DROP TABLE IF EXISTS session_messages")
